import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  input,
  output,
  viewChild,
} from '@angular/core';

@Component({
  selector: 'app-gestion-modal',

  standalone: true,

  templateUrl:
    './modal.component.html',

  styleUrl:
    './modal.component.scss',
})
export class ModalComponent
  implements AfterViewInit, OnDestroy
{
  readonly titulo =
    input.required<string>();

  readonly subtitulo =
    input<string | null>(null);

  readonly amplio =
    input(false);

  readonly lateral =
    input(false);

  readonly compacto =
    input(false);

  readonly operativo =
    input(false);

  readonly ocupado =
    input(false);

  readonly cerrar =
    output<void>();

  private readonly dialog =
    viewChild.required<
      ElementRef<HTMLDialogElement>
    >('dialog');

  private anterior:
    HTMLElement | null = null;

  ngAfterViewInit() {
    this.anterior =
      document.activeElement as HTMLElement;

    this.dialog()
      .nativeElement
      .showModal();
  }

  cancelar(event: Event) {
    event.preventDefault();

    if (!this.ocupado()) {
      this.cerrar.emit();
    }
  }

  ngOnDestroy() {
    this.dialog()
      .nativeElement
      .close();

    this.anterior?.focus();
  }
}