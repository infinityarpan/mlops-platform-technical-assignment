import { Injectable, inject } from '@angular/core';
import { OAuthService } from 'angular-oauth2-oidc';
import { environment } from '../environments/environment';

const ROLE_PRIORITY = ['admin', 'operator', 'approver', 'viewer'];

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly oauth = inject(OAuthService);

  configure(): void {
    if (environment.authMode !== 'oidc') {
      return;
    }
    this.oauth.configure({
      issuer: environment.keycloak.issuer,
      clientId: environment.keycloak.clientId,
      responseType: 'code',
      scope: environment.keycloak.scope,
      redirectUri: window.location.origin,
      postLogoutRedirectUri: window.location.origin,
      showDebugInformation: false,
      requireHttps: false
    });
  }

  initLoginFlow(): Promise<boolean> {
    if (environment.authMode !== 'oidc') {
      return Promise.resolve(true);
    }
    this.configure();
    return this.oauth.loadDiscoveryDocumentAndTryLogin();
  }

  login(): void {
    this.oauth.initLoginFlow();
  }

  logout(): void {
    this.oauth.logOut();
  }

  isAuthenticated(): boolean {
    return environment.authMode !== 'oidc' || this.oauth.hasValidAccessToken();
  }

  accessToken(): string {
    return this.oauth.getAccessToken();
  }

  username(): string {
    const claims = this.oauth.getIdentityClaims() as { preferred_username?: string } | null;
    return claims?.preferred_username ?? 'unknown';
  }

  effectiveRole(): string {
    if (environment.authMode !== 'oidc') {
      return 'admin';
    }
    const claims = this.oauth.getIdentityClaims() as {
      realm_access?: { roles?: string[] };
    } | null;
    const roles = new Set((claims?.realm_access?.roles ?? []).map((role) => role.toLowerCase()));
    return ROLE_PRIORITY.find((role) => roles.has(role)) ?? 'viewer';
  }
}
