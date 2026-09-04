import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { ApiService } from './api.service';

describe('ApiService', () => {
  let service: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists models from the public API', () => {
    let result: unknown;
    service.listModels().subscribe((rows) => (result = rows));
    const req = http.expectOne('/api/models');
    expect(req.request.method).toBe('GET');
    req.flush([]);
    expect(result).toEqual([]);
  });

  it('posts a deployment request', () => {
    service.createDeployment({ model_id: 'm1', version: '1.0.0', environment: 'staging' }).subscribe();
    const req = http.expectOne('/api/deployments');
    expect(req.request.method).toBe('POST');
    req.flush({ id: 'd1' });
  });
});
