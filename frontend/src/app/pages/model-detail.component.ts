import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { forkJoin } from 'rxjs';
import { ApiService } from '../api.service';
import { MetricSample, ModelDetail, ModelVersion } from '../models';
import { StatusPanelComponent } from '../status-panel.component';

@Component({
  selector: 'app-model-detail',
  standalone: true,
  imports: [
    FormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    StatusPanelComponent
  ],
  template: `
    <a routerLink="/">Back to inventory</a>
    <h1>{{ model?.name || 'Model' }}</h1>
    <app-status-panel [loading]="loading" [error]="error" />
    @if (model) {
      <p>{{ model.owner }} · {{ model.id }}</p>
      <div class="grid">
        @for (version of model.versions; track version.id) {
          <mat-card>
            <mat-card-title>{{ version.version }}</mat-card-title>
            <mat-card-content>
              <p>Stage: {{ version.lifecycle_stage }}</p>
              <p>Approved: {{ version.approved }}</p>
              <p>Framework: {{ version.framework || 'n/a' }}</p>
              <p>Artifact: {{ version.artifact_uri }}</p>
            </mat-card-content>
            <mat-card-actions>
              <button mat-stroked-button (click)="approve(version)" [disabled]="version.approved">Approve</button>
            </mat-card-actions>
          </mat-card>
        }
      </div>
      <h2>Version comparison</h2>
      <div class="row">
        <mat-form-field appearance="outline">
          <mat-label>Left</mat-label>
          <mat-select [(ngModel)]="left">
            @for (v of model.versions; track v.id) {
              <mat-option [value]="v.version">{{ v.version }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Right</mat-label>
          <mat-select [(ngModel)]="right">
            @for (v of model.versions; track v.id) {
              <mat-option [value]="v.version">{{ v.version }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
        <button mat-flat-button color="primary" (click)="compare()">Compare latest metrics</button>
      </div>
      @if (leftMetrics || rightMetrics) {
        <div class="grid">
          <mat-card>
            <mat-card-title>{{ left }}</mat-card-title>
            <mat-card-content>
              <p>Latency: {{ leftMetrics?.latency_ms ?? 'n/a' }}</p>
              <p>Quality: {{ leftMetrics?.quality_score ?? 'n/a' }}</p>
              <p>Drift: {{ leftMetrics?.drift_score ?? 'n/a' }}</p>
            </mat-card-content>
          </mat-card>
          <mat-card>
            <mat-card-title>{{ right }}</mat-card-title>
            <mat-card-content>
              <p>Latency: {{ rightMetrics?.latency_ms ?? 'n/a' }}</p>
              <p>Quality: {{ rightMetrics?.quality_score ?? 'n/a' }}</p>
              <p>Drift: {{ rightMetrics?.drift_score ?? 'n/a' }}</p>
            </mat-card-content>
          </mat-card>
        </div>
      }
    }
  `,
  styles: [`
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  `]
})
export class ModelDetailComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  model: ModelDetail | null = null;
  loading = true;
  error: string | null = null;
  left = '';
  right = '';
  leftMetrics: MetricSample | null = null;
  rightMetrics: MetricSample | null = null;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.api.getModel(id).subscribe({
      next: (model) => {
        this.model = model;
        this.left = model.versions[0]?.version ?? '';
        this.right = model.versions[1]?.version ?? this.left;
        this.loading = false;
      },
      error: (err: Error) => {
        this.error = err.message;
        this.loading = false;
      }
    });
  }

  approve(version: ModelVersion): void {
    this.api.approveVersion(version.model_id, version.version).subscribe({
      next: (updated) => {
        version.approved = updated.approved;
        version.lifecycle_stage = updated.lifecycle_stage;
      },
      error: (err: Error) => (this.error = err.message)
    });
  }

  compare(): void {
    if (!this.model) {
      return;
    }
    forkJoin({
      left: this.api.metrics(this.model.id, this.left),
      right: this.api.metrics(this.model.id, this.right)
    }).subscribe({
      next: ({ left, right }) => {
        this.leftMetrics = left.latest ?? null;
        this.rightMetrics = right.latest ?? null;
      },
      error: (err: Error) => (this.error = err.message)
    });
  }
}
