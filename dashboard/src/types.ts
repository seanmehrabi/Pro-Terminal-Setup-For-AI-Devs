export interface HostInfo {
  os: string;
  arch: string;
  distro: string;
  memory_bytes: number;
  disk_free_bytes: number;
  home: string;
  brew: boolean;
  winget: boolean;
}

export interface ApplicationStatus {
  id: string;
  installed: boolean;
  version: string;
  action: string;
  detail: string;
}

export interface StatusPayload {
  host: HostInfo;
  applications: ApplicationStatus[];
}

export interface StatusApiResponse {
  auth: { ok: boolean };
  status: StatusPayload | null;
  error: string | null;
}

declare global {
  interface Window {
    __DASHBOARD_TOKEN__?: string;
  }
}
