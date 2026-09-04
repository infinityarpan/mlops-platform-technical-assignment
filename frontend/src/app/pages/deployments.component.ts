import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { ApiService } from '../api.service';
import { Deployment } from '../models';
import { StatusPanelComponent } from '../status-panel.component';

@Component({
  selector: 'app-deployments',
  standalone: true,
  imports: [
    FormsModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatCheckboxModule,
    StatusPanelComponent
  ],
  template: `
    <h1>Deployments</h1>
    <form class="row" (ngSubmit)="deploy()">
      <mat-form-field appearance="outline">
        <mat-label>Model id</mat-label>
        <input matInput name="modelId" [(ngModel)]="modelId" required />
      </mat-form-field>
      <mat-form-field appearance="outline">
        <mat-label>Version</mat-label>
        <input matInput name="version" [(ngModel)]="version" required />
      </mat-form-field>
      <mat-form-field appearance="outline">
        <mat-label>Environment</mat-label>
        <mat-select name="environment" [(ngModel)]="environment">
          <mat-option value="staging">staging</mat-option>
          <mat-option value="production">production</mat-option>
        </mat-select>
      </mat-form-field>
      <mat-checkbox [(ngModel)]="simulateFailure" name="fail">Simulate failure</mat-checkbox>
      <button mat-flat-button color="primary" type="submit">Deploy</button>
    </form>
    <app-status-panel [loading]="loading" [empty]="!loading && rows.length === 0" [error]="error" />
    @if (rows.length) {
      <table mat-table [dataSource]="rows" class="mat-elevation-z1">
        <ng-container matColumnDef="id">
          <th mat-header-cell *matHeaderCellDef>Id</th>
          <td mat-cell *matCellDef="let row">{{ row.id }}</td>
        </ng-container>
        <ng-container matColumnDef="model">
          <th mat-header-cell *matHeaderCellDef>Model</th>
          <td mat-cell *matCellDef="let row">{{ row.model_id }}:{{ row.version }}</td>
        </ng-container>
        <ng-container matColumnDef="env">
          <th mat-header-cell *matHeaderCellDef>Env</th>
          <td mat-cell *matCellDef="let row">{{ row.environment }}</td>
        </ng-container>
        <ng-container matColumnDef="status">
          <th mat-header-cell *matHeaderCellDef>Status</th>
          <td mat-cell *matCellDef="let row">{{ row.status }}</td>
        </ng-container>
        <ng-container matColumnDef="actions">
          <th mat-header-cell *matHeaderCellDef></th>
          <td mat-cell *matCellDef="let row">
            <button mat-button (click)="retry(row)" [disabled]="row.status !== 'FAILED'">Retry</button>
            <button mat-button (click)="rollback(row)" [disabled]="row.status !== 'SUCCEEDED' || row.environment !== 'production'">Rollback</button>
          </td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="columns"></tr>
        <tr mat-row *matRowDef="let row; columns: columns;"></tr>
      </table>
    }
  `,
  styles: [`.row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }`]
})
export class DeploymentsComponent implements OnInit {
  private readonly api = inject(ApiService);
  rows: Deployment[] = [];
  loading = true;
  error: string | null = null;
  modelId = 'pump-failure-predictor';
  version = '2.0.0';
  environment = 'production';
  simulateFailure = false;
  columns = ['id', 'model', 'env', 'status', 'actions'];

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading = true;
    this.api.listDeployments().subscribe({
      next: (rows) => {
        this.rows = rows;
        this.loading = false;
      },
      error: (err: Error) => {
        this.error = err.message;
        this.loading = false;
      }
    });
  }

  deploy(): void {
    this.error = null;
    this.api
      .createDeployment({
        model_id: this.modelId,
        version: this.version,
        environment: this.environment,
        simulate_failure: this.simulateFailure,
        idempotency_key: `${this.modelId}:${this.version}:${this.environment}:${Date.now()}`
      })
      .subscribe({
        next: () => this.refresh(),
        error: (err: Error) => (this.error = err.message)
      });
  }

  retry(row: Deployment): void {
    this.api.retry(row.id).subscribe({
      next: () => this.refresh(),
      error: (err: Error) => (this.error = err.message)
    });
  }

  rollback(row: Deployment): void {
    this.api.rollback(row.id).subscribe({
      next: () => this.refresh(),
      error: (err: Error) => (this.error = err.message)
    });
  }
}
