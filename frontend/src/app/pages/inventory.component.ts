import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTableModule } from '@angular/material/table';
import { ApiService } from '../api.service';
import { ModelSummary } from '../models';
import { StatusPanelComponent } from '../status-panel.component';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [
    FormsModule,
    RouterLink,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    StatusPanelComponent
  ],
  template: `
    <h1>Model inventory</h1>
    <mat-form-field appearance="outline" class="full">
      <mat-label>Search name, owner or id</mat-label>
      <input matInput [(ngModel)]="query" />
    </mat-form-field>
    <app-status-panel [loading]="loading" [empty]="!loading && filtered.length === 0" [error]="error" />
    @if (!loading && filtered.length) {
      <table mat-table [dataSource]="filtered" class="mat-elevation-z1">
        <ng-container matColumnDef="name">
          <th mat-header-cell *matHeaderCellDef>Name</th>
          <td mat-cell *matCellDef="let row"><a [routerLink]="['/models', row.id]">{{ row.name }}</a></td>
        </ng-container>
        <ng-container matColumnDef="owner">
          <th mat-header-cell *matHeaderCellDef>Owner</th>
          <td mat-cell *matCellDef="let row">{{ row.owner }}</td>
        </ng-container>
        <ng-container matColumnDef="versions">
          <th mat-header-cell *matHeaderCellDef>Versions</th>
          <td mat-cell *matCellDef="let row">{{ row.version_count }}</td>
        </ng-container>
        <ng-container matColumnDef="production">
          <th mat-header-cell *matHeaderCellDef>Production</th>
          <td mat-cell *matCellDef="let row">{{ row.production_version || '—' }}</td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="columns"></tr>
        <tr mat-row *matRowDef="let row; columns: columns;"></tr>
      </table>
    }
  `
})
export class InventoryComponent implements OnInit {
  private readonly api = inject(ApiService);
  models: ModelSummary[] = [];
  query = '';
  loading = true;
  error: string | null = null;
  columns = ['name', 'owner', 'versions', 'production'];

  get filtered(): ModelSummary[] {
    const q = this.query.toLowerCase().trim();
    if (!q) {
      return this.models;
    }
    return this.models.filter(
      (m) => m.name.toLowerCase().includes(q) || m.owner.toLowerCase().includes(q) || m.id.includes(q)
    );
  }

  ngOnInit(): void {
    this.api.listModels().subscribe({
      next: (rows) => {
        this.models = rows;
        this.loading = false;
      },
      error: (err: Error) => {
        this.error = err.message;
        this.loading = false;
      }
    });
  }
}
