import {
  Component,
  ElementRef,
  ViewChild,
  AfterViewInit,
  OnDestroy,
  NgZone,
  HostListener
} from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-tiger-mascot',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative flex items-center justify-center pointer-events-none select-none">
      <!-- Hidden video element kept in layout tree for hardware video decoding -->
      <video
        #videoEl
        src="/tiger.mp4"
        autoplay
        loop
        muted
        playsinline
        preload="auto"
        crossorigin="anonymous"
        style="position: absolute; width: 320px; height: 180px; opacity: 0.001; pointer-events: none; z-index: -1;"
        (error)="onVideoError($event)"
      ></video>
      <canvas
        #canvasEl
        class="w-48 sm:w-56 md:w-64 lg:w-72 h-auto drop-shadow-2xl select-none pointer-events-none"
      ></canvas>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      pointer-events: none;
      user-select: none;
    }
  `]
})
export class TigerMascotComponent implements AfterViewInit, OnDestroy {
  @ViewChild('videoEl') videoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('canvasEl') canvasRef!: ElementRef<HTMLCanvasElement>;

  private isDestroyed = false;
  private animFrameId: number | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private renderWidth = 0;
  private renderHeight = 0;
  private hasFallbackTried = false;
  private hasLoggedFirstFrame = false;

  constructor(private ngZone: NgZone) {}

  @HostListener('window:click')
  @HostListener('window:keydown')
  onUserInteraction(): void {
    const video = this.videoRef?.nativeElement;
    if (video && video.paused) {
      video.play().catch(() => {});
    }
  }

  ngAfterViewInit(): void {
    const video = this.videoRef?.nativeElement;
    const canvas = this.canvasRef?.nativeElement;
    if (!video || !canvas) return;

    this.ctx = canvas.getContext('2d', { willReadFrequently: true });

    // Enforce video properties
    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;
    video.crossOrigin = 'anonymous';
    video.setAttribute('muted', '');
    video.setAttribute('playsinline', '');
    video.setAttribute('crossorigin', 'anonymous');

    const initSizeAndStart = () => {
      if (this.isDestroyed) return;
      if (video.videoWidth > 0 && video.videoHeight > 0) {
        if (this.renderWidth === 0) {
          const maxWidth = 480;
          const scale = video.videoWidth > maxWidth ? maxWidth / video.videoWidth : 1;
          this.renderWidth = Math.round(video.videoWidth * scale);
          this.renderHeight = Math.round(video.videoHeight * scale);

          canvas.width = this.renderWidth;
          canvas.height = this.renderHeight;
          console.log(`%c[Tiger Mascot] Video initialized: ${video.videoWidth}x${video.videoHeight} -> Canvas: ${this.renderWidth}x${this.renderHeight}`, 'color: #059669; font-weight: bold;');
        }
      }
    };

    video.addEventListener('loadedmetadata', initSizeAndStart);
    video.addEventListener('loadeddata', initSizeAndStart);
    video.addEventListener('canplay', () => {
      initSizeAndStart();
      video.play().catch(() => {});
    });
    video.addEventListener('play', initSizeAndStart);

    if (video.readyState >= 1) {
      initSizeAndStart();
    }

    this.ngZone.runOutsideAngular(() => {
      video.play().catch(() => {});
      this.startLoop();
    });
  }

  onVideoError(event: any): void {
    const video = this.videoRef?.nativeElement;
    console.warn('[Tiger Mascot] Primary video load issue, attempting fallback source:', {
      code: video?.error?.code,
      message: video?.error?.message,
      currentSrc: video?.currentSrc
    });
    if (this.hasFallbackTried || !video) return;
    this.hasFallbackTried = true;
    if (video.src.includes('uploads/tiger.mp4')) {
      video.src = '/tiger.mp4';
    } else {
      video.src = 'http://localhost:5000/uploads/tiger.mp4';
    }
    video.load();
    video.play().catch(() => {});
  }

  private startLoop(): void {
    const video = this.videoRef?.nativeElement;
    const canvas = this.canvasRef?.nativeElement;
    if (!video || !canvas) return;

    const render = () => {
      if (this.isDestroyed) return;

      // Draw whenever video has dimensions, even if readyState is 1 (metadata loaded)
      if (video.videoWidth > 0) {
        if (this.renderWidth === 0) {
          const maxWidth = 480;
          const scale = video.videoWidth > maxWidth ? maxWidth / video.videoWidth : 1;
          this.renderWidth = Math.round(video.videoWidth * scale);
          this.renderHeight = Math.round(video.videoHeight * scale);
          canvas.width = this.renderWidth;
          canvas.height = this.renderHeight;
        }

        this.processFrame(video);
      }

      this.animFrameId = requestAnimationFrame(render);
    };

    this.animFrameId = requestAnimationFrame(render);
  }

  private processFrame(video: HTMLVideoElement): void {
    if (!this.ctx || this.renderWidth <= 0 || this.renderHeight <= 0) return;

    try {
      // 1. Draw raw video frame onto canvas
      this.ctx.drawImage(video, 0, 0, this.renderWidth, this.renderHeight);

      // 2. Read pixels for chroma keying
      const imgData = this.ctx.getImageData(0, 0, this.renderWidth, this.renderHeight);
      const d = imgData.data;
      const len = d.length;

      // Chroma key thresholds:
      // Green backdrop has: g - max(r, b) > 25
      // Tiger fur is white/gray/black: g ≈ r ≈ b, diff ≈ 0
      const thresholdLow = 14;
      const thresholdHigh = 34;
      const thresholdRange = thresholdHigh - thresholdLow;

      for (let i = 0; i < len; i += 4) {
        const r = d[i];
        const g = d[i + 1];
        const b = d[i + 2];
        const maxRb = r > b ? r : b;
        const diff = g - maxRb;

        if (diff > thresholdHigh) {
          // Pure green backdrop -> 100% transparent
          d[i + 3] = 0;
        } else if (diff > thresholdLow) {
          // Edge feathering
          const factor = (thresholdHigh - diff) / thresholdRange;
          d[i + 3] = Math.round(d[i + 3] * factor);
          d[i + 1] = maxRb; // despill
        } else if (diff > 0) {
          // Soft despill
          d[i + 1] = maxRb;
        }
      }

      this.ctx.putImageData(imgData, 0, 0);

      if (!this.hasLoggedFirstFrame) {
        this.hasLoggedFirstFrame = true;
        console.log('%c[Tiger Mascot] First frame rendered successfully with Chroma-Key!', 'color: #10b981; font-weight: bold;');
      }
    } catch (err) {
      console.error('[Tiger Mascot] Chroma processing error:', err);
    }
  }

  ngOnDestroy(): void {
    this.isDestroyed = true;
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    const video = this.videoRef?.nativeElement;
    if (video) {
      video.pause();
      video.removeAttribute('src');
      video.load();
    }
    this.ctx = null;
  }
}
