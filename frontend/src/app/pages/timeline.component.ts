import { Component, OnInit, inject } from '@angular/core';
import { MatListModule } from '@angular/material/list';
import { ApiService } from '../api.service';
import { Deployment } from '../models';
import { StatusPanelComponent } from '../status-panel.component';

@Component({
  selector: 'app-timeline',
  standalone: true,
  imports: [MatListModule, StatusPanelComponent],
  template: `
    <h1>Event timeline</h1>
    <app-status-panel [loading]="loading" [empty]="!loading && events.length === 0" [error]="error" />
    <mat-nav-list>
      @for (item of events; track item.key) {
        <a mat-list-item>
          <span matListItemTitle>{{ item.when }} · {{ item.model }}:{{ item.version }}</span>
          <span matListItemLine>{{ item.event }} ({{ item.status }})</span>
        </a>
      }
    </mat-nav-list>
  `
})
export class TimelineComponent implements OnInit {
  private readonly api = inject(ApiService);
  events: { key: string; when: string; model: string; version: string; event: string; status: string }[] = [];
  loading = true;
  error: string | null = null;

  ngOnInit(): void {
    this.api.listDeployments().subscribe({
      next: (rows: Deployment[]) => {
        this.events = rows
          .flatMap((row) =>
            (row.events || []).map((event) => ({
              key: event.id,
              when: event.created_at,
              model: row.model_id,
              version: row.version,
              event: event.event,
              status: event.status
            }))
          )
          .sort((a, b) => a.when.localeCompare(b.when))
          .reverse();
        this.loading = false;
      },
      error: (err: Error) => {
        this.error = err.message;
        this.loading = false;
      }
    });
  }
}
