import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { ApiService } from '../api.service';
import { MetricSample, MetricsResponse } from '../models';
import { StatusPanelComponent } from '../status-panel.component';

@Component({
  selector: 'app-monitoring',
  standalone: true,
  imports: [FormsModule, MatCardModule, MatFormFieldModule, MatInputModule, MatButtonModule, StatusPanelComponent],
  template: `
    <h1>Monitoring</h1>
    <form class="row" (ngSubmit)="load()">
      <mat-form-field appearance="outline">
        <mat-label>Model id</mat-label>
        <input matInput name="modelId" [(ngModel)]="modelId" />
      </mat-form-field>
      <button mat-flat-button color="primary">Load</button>
    </form>
    <app-status-panel [loading]="loading" [empty]="!loading && !latest" [error]="error" />
    @if (latest) {
      <div class="grid">
        <mat-card><mat-card-title>Latency</mat-card-title><mat-card-content>{{ latest.latency_ms }} ms</mat-card-content></mat-card>
        <mat-card><mat-card-title>Throughput</mat-card-title><mat-card-content>{{ latest.throughput_rpm }} rpm</mat-card-content></mat-card>
        <mat-card><mat-card-title>Error rate</mat-card-title><mat-card-content>{{ latest.error_rate }}</mat-card-content></mat-card>
        <mat-card><mat-card-title>Quality</mat-card-title><mat-card-content>{{ latest.quality_score }}</mat-card-content></mat-card>
        <mat-card><mat-card-title>Drift</mat-card-title><mat-card-content>{{ latest.drift_score }}</mat-card-content></mat-card>
        <mat-card><mat-card-title>Availability</mat-card-title><mat-card-content>{{ latest.availability }}%</mat-card-content></mat-card>
        <mat-card><mat-card-title>Status</mat-card-title><mat-card-content>{{ latest.monitoring_status }}</mat-card-content></mat-card>
        <mat-card><mat-card-title>Last inference</mat-card-title><mat-card-content>{{ latest.last_successful_inference }}</mat-card-content></mat-card>
      </div>
      <h2>Recent samples</h2>
      <ul>
        @for (sample of samples.slice(-8); track sample.timestamp) {
          <li>{{ sample.timestamp }} · v{{ sample.version }} · {{ sample.latency_ms }} ms · drift {{ sample.drift_score }}</li>
        }
      </ul>
    }
  `,
  styles: [`
    .row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
  `]
})
export class MonitoringComponent implements OnInit {
  private readonly api = inject(ApiService);
  modelId = 'pump-failure-predictor';
  latest: MetricSample | null = null;
  samples: MetricSample[] = [];
  loading = false;
  error: string | null = null;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.error = null;
    this.api.metrics(this.modelId).subscribe({
      next: (resp: MetricsResponse) => {
        this.samples = resp.samples;
        this.latest = resp.latest ?? null;
        this.loading = false;
      },
      error: (err: Error) => {
        this.error = err.message;
        this.latest = null;
        this.loading = false;
      }
    });
  }
}
