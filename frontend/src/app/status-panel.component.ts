import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-status-panel',
  standalone: true,
  imports: [MatCardModule],
  template: `
    @if (loading) {
      <mat-card class="panel"><mat-card-content>Loading…</mat-card-content></mat-card>
    }
    @if (!loading && empty) {
      <mat-card class="panel"><mat-card-content>No records found.</mat-card-content></mat-card>
    }
    @if (error) {
      <mat-card class="panel error">
        <mat-card-title>Request failed</mat-card-title>
        <mat-card-content>{{ error }}</mat-card-content>
      </mat-card>
    }
  `,
  styles: [`
    .panel { margin: 12px 0; }
    .error { border-left: 4px solid #c62828; }
  `]
})
export class StatusPanelComponent {
  @Input() loading = false;
  @Input() empty = false;
  @Input() error: string | null = null;
}
