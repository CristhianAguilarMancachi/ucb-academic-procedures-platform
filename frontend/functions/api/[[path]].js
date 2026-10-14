const BACKEND_ORIGIN = 'https://ucb-tramites-api.onrender.com';

export async function onRequest({ request }) {
  const incomingUrl = new URL(request.url);
  const targetUrl = new URL(
    incomingUrl.pathname + incomingUrl.search,
    BACKEND_ORIGIN
  );

  const headers = new Headers(request.headers);

  headers.delete('host');
  headers.delete('content-length');

  const upstreamRequest = new Request(targetUrl.toString(), {
    method: request.method,
    headers,
    body:
      request.method === 'GET' || request.method === 'HEAD'
        ? undefined
        : request.body,
    redirect: 'manual',
  });

  try {
    const upstreamResponse = await fetch(upstreamRequest);

    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
      headers: upstreamResponse.headers,
    });
  } catch {
    return Response.json(
      {
        detail: 'El servidor no está disponible temporalmente.',
      },
      { status: 502 }
    );
  }
}
