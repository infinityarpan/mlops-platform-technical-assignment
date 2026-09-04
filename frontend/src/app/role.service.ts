import { Injectable, signal } from '@angular/core';

const STORAGE_KEY = 'mlops.actorRole';

@Injectable({ providedIn: 'root' })
export class RoleService {
  readonly role = signal(localStorage.getItem(STORAGE_KEY) ?? 'admin');

  setRole(role: string): void {
    this.role.set(role);
    localStorage.setItem(STORAGE_KEY, role);
  }
}
