import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth.service';
import { RoleService } from './role.service';
import { environment } from '../environments/environment';

export const apiInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const role = inject(RoleService);
  const correlationId = crypto.randomUUID();
  const headers: Record<string, string> = {
    'X-Correlation-ID': correlationId
  };

  if (environment.authMode === 'oidc') {
    const token = auth.accessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  } else {
    headers['X-Actor-Role'] = role.role();
  }

  const authReq = req.clone({ setHeaders: headers });
  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      const problem = error.error;
      const message =
        problem?.title && problem?.detail
          ? `${problem.title}: ${typeof problem.detail === 'string' ? problem.detail : JSON.stringify(problem.detail)}`
          : error.message;
      return throwError(() => new Error(message));
    })
  );
};
