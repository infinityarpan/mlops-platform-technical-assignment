export interface ModelSummary {
  id: string;
  name: string;
  owner: string;
  description?: string | null;
  created_at: string;
  version_count: number;
  production_version?: string | null;
}

export interface ModelVersion {
  id: string;
  model_id: string;
  version: string;
  framework?: string | null;
  algorithm?: string | null;
  artifact_uri: string;
  training_data_ref?: string | null;
  tags: string[];
  extra_metadata: Record<string, unknown>;
  approved: boolean;
  lifecycle_stage: string;
  lock_version: number;
  created_at: string;
  updated_at: string;
}

export interface ModelDetail {
  id: string;
  name: string;
  owner: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  versions: ModelVersion[];
}

export interface DeploymentEvent {
  id: string;
  event: string;
  status: string;
  message?: string | null;
  created_at: string;
}

export interface Deployment {
  id: string;
  model_id: string;
  version_id: string;
  version: string;
  environment: string;
  status: string;
  idempotency_key?: string | null;
  previous_deployment_id?: string | null;
  failure_reason?: string | null;
  failure_class?: string | null;
  simulate_failure: boolean;
  correlation_id?: string | null;
  created_at: string;
  updated_at: string;
  events: DeploymentEvent[];
}

export interface MetricSample {
  timestamp: string;
  model_id: string;
  version: string;
  environment: string;
  latency_ms: number;
  throughput_rpm: number;
  error_rate: number;
  quality_score: number;
  drift_score: number;
  availability: number;
  last_successful_inference?: string | null;
  monitoring_status: string;
}

export interface MetricsResponse {
  model_id: string;
  samples: MetricSample[];
  latest?: MetricSample | null;
}

export interface ApiProblem {
  type?: string;
  title: string;
  status: number;
  detail: unknown;
  instance?: string;
}
