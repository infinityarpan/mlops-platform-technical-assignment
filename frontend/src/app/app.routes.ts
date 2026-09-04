import { Routes } from '@angular/router';
import { InventoryComponent } from './pages/inventory.component';
import { ModelDetailComponent } from './pages/model-detail.component';
import { DeploymentsComponent } from './pages/deployments.component';
import { MonitoringComponent } from './pages/monitoring.component';
import { TimelineComponent } from './pages/timeline.component';

export const routes: Routes = [
  { path: '', component: InventoryComponent },
  { path: 'models/:id', component: ModelDetailComponent },
  { path: 'deployments', component: DeploymentsComponent },
  { path: 'monitoring', component: MonitoringComponent },
  { path: 'timeline', component: TimelineComponent }
];
