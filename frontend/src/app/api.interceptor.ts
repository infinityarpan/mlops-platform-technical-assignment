import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { RoleService } from './role.service';

export const apiInterceptor: HttpInterceptorFn = (req, next) => {
  const role = inject(RoleService).role();
  const correlationId = crypto.randomUUID();
  const authReq = req.clone({
    setHeaders: {
      'X-Actor-Role': role,
      'X-Correlation-ID': correlationId
    }
  });
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
