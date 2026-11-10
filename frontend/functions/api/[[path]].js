
const BACKEND_ORIGIN = 'https://ucb-tramites-api.onrender.com';

const RECOVERY_HEADER = 'hibernate-rate-limited';

const RECOVERY_MAX_DURATION_MS = 75_000;
const RECOVERY_MAX_ATTEMPTS = 6;
const RECOVERY_INTERVAL_MS = 4_000;
const RECOVERY_FETCH_TIMEOUT_MS = 40_000;

function isHibernateRateLimited(response) {
  return (
    response?.status === 429 &&
    response.headers
      .get('x-render-routing')
      ?.trim()
      .toLowerCase() === RECOVERY_HEADER
  );
}

function isTemporaryBackendFailure(response) {
  return (
    response === null ||
    isHibernateRateLimited(response) ||
    response.status === 502 ||
    response.status === 503 ||
    response.status === 504
  );
}

function isGoogleConfigRequest(method, pathname) {
  return (
    method === 'GET' &&
    pathname === '/api/auth/google/config'
  );
}

function isLoginRequest(method, pathname) {
  return (
    method === 'POST' &&
    (
      pathname === '/api/auth/login' ||
      pathname.startsWith('/api/auth/google/')
    )
  );
}

function sleep(milliseconds) {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}

async function checkBackend(timeoutMs) {
  const url = new URL('/health', BACKEND_ORIGIN);

  try {
    return await fetch(url.toString(), {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      redirect: 'manual',
      cache: 'no-store',
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch {
    return null;
  }
}

async function recoverBackend() {
  const deadline =
    Date.now() + RECOVERY_MAX_DURATION_MS;

  for (
    let attempt = 0;
    attempt < RECOVERY_MAX_ATTEMPTS;
    attempt += 1
  ) {
    const remaining = deadline - Date.now();

    if (remaining <= 0) {
      return false;
    }

    const response = await checkBackend(
      Math.min(
        RECOVERY_FETCH_TIMEOUT_MS,
        remaining
      )
    );

    if (response?.ok) {
      return true;
    }

    if (!isTemporaryBackendFailure(response)) {
      return false;
    }

    if (attempt === RECOVERY_MAX_ATTEMPTS - 1) {
      return false;
    }

    const remainingAfterRequest =
      deadline - Date.now();

    if (remainingAfterRequest <= 0) {
      return false;
    }

    await sleep(
      Math.min(
        RECOVERY_INTERVAL_MS,
        remainingAfterRequest
      )
    );
  }

  return false;
}

function unavailableResponse() {
  return Response.json(
    {
      detail:
        'El servidor académico está iniciando. ' +
        'Intenta nuevamente en unos momentos.',
    },
    {
      status: 503,
      headers: {
        'Cache-Control': 'no-store',
        'Retry-After': '10',
        'X-Backend-Recovery': 'not-ready',
        'X-UCB-Proxy': 'render-recovery-v1',
        'X-UCB-Recovery': 'failed',
      },
    }
  );
}

function makeUpstreamRequest(
  request,
  targetUrl,
  headers
) {
  const hasBody =
    request.method !== 'GET' &&
    request.method !== 'HEAD' &&
    request.body !== null;

  const options = {
    method: request.method,
    headers,
    redirect: 'manual',
  };

  if (hasBody) {
    options.body = request.body;

    // Necesario al reconstruir solicitudes
    // con cuerpo ReadableStream en Node.js.
    // También conserva el envío por streaming.
    options.duplex = 'half';
  }

  return new Request(
    targetUrl.toString(),
    options
  );
}

async function forwardRequest(
  request,
  targetUrl,
  headers
) {
  const upstreamRequest = makeUpstreamRequest(
    request,
    targetUrl,
    headers
  );

  return fetch(upstreamRequest);
}

function relayResponse(
  upstreamResponse,
  recoveryStatus = 'not-needed'
) {
  const responseHeaders = new Headers(
    upstreamResponse.headers
  );

  responseHeaders.set(
    'X-UCB-Proxy',
    'render-recovery-v1'
  );

  responseHeaders.set(
    'X-UCB-Recovery',
    recoveryStatus
  );

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: responseHeaders,
  });
}

export async function onRequest({ request }) {
  const incomingUrl = new URL(request.url);

  const targetUrl = new URL(
    incomingUrl.pathname + incomingUrl.search,
    BACKEND_ORIGIN
  );

  const headers = new Headers(request.headers);

  headers.delete('host');
  headers.delete('content-length');

  const googleConfigRequest = isGoogleConfigRequest(
    request.method,
    incomingUrl.pathname
  );

  const loginRequest = isLoginRequest(
    request.method,
    incomingUrl.pathname
  );

  try {
    // Comprobación de disponibilidad previa
    // al envío de credenciales.
    if (loginRequest) {
      const readiness = await checkBackend(
        RECOVERY_FETCH_TIMEOUT_MS
      );

      if (isTemporaryBackendFailure(readiness)) {
        const recovered = await recoverBackend();

        if (!recovered) {
          return unavailableResponse();
        }
      } else if (!readiness.ok) {
        // No enviar credenciales si la verificación
        // recibió otro error inesperado.
        return unavailableResponse();
      }
    }

    const upstreamResponse = await forwardRequest(
      request,
      targetUrl,
      headers
    );

    // Recuperación automática únicamente
    // para GET público de configuración Google.
    if (
      googleConfigRequest &&
      isHibernateRateLimited(upstreamResponse)
    ) {
      const recovered = await recoverBackend();

      if (!recovered) {
        return unavailableResponse();
      }

      const retryResponse = await forwardRequest(
        request,
        targetUrl,
        headers
      );

      return relayResponse(retryResponse, 'recovered');
    }

    // No repetir POST ni operaciones de escritura.
    return relayResponse(upstreamResponse);
  } catch {
    return Response.json(
      {
        detail:
          'El servidor no está disponible ' +
          'temporalmente.',
      },
      {
        status: 502,
        headers: {
          'Cache-Control': 'no-store',
          'X-UCB-Proxy': 'render-recovery-v1',
          'X-UCB-Recovery': 'error',
        },
      }
    );
  }
}
