import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';
import {
  Deployment,
  DeploymentEvent,
  MetricsResponse,
  ModelDetail,
  ModelSummary,
  ModelVersion
} from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  listModels(): Observable<ModelSummary[]> {
    return this.http.get<ModelSummary[]>(`${this.base}/models`);
  }

  getModel(id: string): Observable<ModelDetail> {
    return this.http.get<ModelDetail>(`${this.base}/models/${id}`);
  }

  listVersions(modelId: string): Observable<ModelVersion[]> {
    return this.http.get<ModelVersion[]>(`${this.base}/models/${modelId}/versions`);
  }

  promoteToStaging(modelId: string, version: string): Observable<ModelVersion> {
    return this.http.post<ModelVersion>(
      `${this.base}/models/${modelId}/versions/${version}/promote-to-staging`,
      {}
    );
  }

  transitionStage(modelId: string, version: string, targetStage: string): Observable<ModelVersion> {
    return this.http.post<ModelVersion>(
      `${this.base}/models/${modelId}/versions/${version}/transition-stage`,
      { target_stage: targetStage }
    );
  }

  listDeployments(modelId?: string): Observable<Deployment[]> {
    let params = new HttpParams();
    if (modelId) {
      params = params.set('model_id', modelId);
    }
    return this.http.get<Deployment[]>(`${this.base}/deployments`, { params });
  }

  createDeployment(body: {
    model_id: string;
    version: string;
    environment: string;
    simulate_failure?: boolean;
    idempotency_key?: string;
  }): Observable<Deployment> {
    return this.http.post<Deployment>(`${this.base}/deployments`, body, {
      headers: body.idempotency_key ? { 'Idempotency-Key': body.idempotency_key } : {}
    });
  }

  retry(id: string): Observable<Deployment> {
    return this.http.post<Deployment>(`${this.base}/deployments/${id}/retry`, {});
  }

  rollback(id: string): Observable<Deployment> {
    return this.http.post<Deployment>(`${this.base}/deployments/${id}/rollback`, {});
  }

  events(id: string): Observable<DeploymentEvent[]> {
    return this.http.get<DeploymentEvent[]>(`${this.base}/deployments/${id}/events`);
  }

  metrics(modelId: string, version?: string): Observable<MetricsResponse> {
    let params = new HttpParams();
    if (version) {
      params = params.set('version', version);
    }
    return this.http.get<MetricsResponse>(`${this.base}/models/${modelId}/metrics`, { params });
  }
}
