import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { RoleService } from './role.service';
import { AuthService } from './auth.service';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    FormsModule,
    MatToolbarModule,
    MatButtonModule,
    MatSelectModule,
    MatFormFieldModule
  ],
  template: `
    <mat-toolbar color="primary">
      <span>MLOps Platform</span>
      <a mat-button routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}">Inventory</a>
      <a mat-button routerLink="/deployments" routerLinkActive="active">Deployments</a>
      <a mat-button routerLink="/monitoring" routerLinkActive="active">Monitoring</a>
      <a mat-button routerLink="/timeline" routerLinkActive="active">Timeline</a>
      <span class="spacer"></span>
      @if (useOidc) {
        @if (auth.isAuthenticated()) {
          <span class="identity">{{ auth.username() }} · {{ auth.effectiveRole() }}</span>
          <button mat-button type="button" (click)="auth.logout()">Logout</button>
        } @else {
          <button mat-flat-button color="accent" type="button" (click)="auth.login()">Login</button>
        }
      } @else {
        <mat-form-field appearance="outline" class="role">
          <mat-label>Role</mat-label>
          <mat-select [ngModel]="role.role()" (ngModelChange)="role.setRole($event)">
            <mat-option value="viewer">viewer</mat-option>
            <mat-option value="approver">approver</mat-option>
            <mat-option value="operator">operator</mat-option>
            <mat-option value="admin">admin</mat-option>
          </mat-select>
        </mat-form-field>
      }
    </mat-toolbar>
    <main class="content">
      <router-outlet />
    </main>
  `,
  styles: [`
    .spacer { flex: 1; }
    .content { padding: 16px; max-width: 1200px; margin: 0 auto; }
    .role { width: 140px; font-size: 14px; }
    .identity { margin-right: 8px; font-size: 14px; }
    a.active { text-decoration: underline; }
    mat-toolbar { flex-wrap: wrap; }
  `]
})
export class AppComponent {
  readonly role = inject(RoleService);
  readonly auth = inject(AuthService);
  readonly useOidc = environment.authMode === 'oidc';
}
