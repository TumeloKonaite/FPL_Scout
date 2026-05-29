import type { FullReportResponse, PipelineRun, ReportSummary } from "../types/report";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? DEFAULT_API_BASE_URL;

export class ApiError extends Error {
  readonly status: number;
  readonly statusText: string;
  readonly detail?: unknown;

  constructor(response: Response, detail?: unknown) {
    super(`API request failed: ${response.status} ${response.statusText}`);
    this.name = "ApiError";
    this.status = response.status;
    this.statusText = response.statusText;
    this.detail = detail;
  }
}

type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  params?: Record<string, string | number | boolean | null | undefined>;
};

function buildUrl(path: string, params?: ApiRequestOptions["params"]): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`);

  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

async function parseJson(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }

  const contentType = response.headers.get("content-type");

  if (!contentType?.includes("application/json")) {
    return undefined;
  }

  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

function createHeaders(headers?: HeadersInit, hasBody = false): Headers {
  const requestHeaders = new Headers(headers);
  requestHeaders.set("Accept", "application/json");

  if (hasBody && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  return requestHeaders;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, headers, params, ...requestOptions } = options;
  const response = await fetch(buildUrl(path, params), {
    ...requestOptions,
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: createHeaders(headers, body !== undefined)
  });

  const responseBody = await parseJson(response);

  if (!response.ok) {
    throw new ApiError(response, responseBody);
  }

  return responseBody as T;
}

export function getReports(): Promise<ReportSummary[]> {
  return apiRequest<ReportSummary[]>("/api/reports");
}

export function getLatestReport(): Promise<FullReportResponse> {
  return apiRequest<FullReportResponse>("/api/reports/latest");
}

export function getReport(runId: string): Promise<FullReportResponse> {
  return apiRequest<FullReportResponse>(`/api/reports/${encodeURIComponent(runId)}`);
}

export function runPipeline(inputData?: Record<string, unknown>): Promise<PipelineRun> {
  return apiRequest<PipelineRun>("/api/pipeline-runs", {
    body: inputData === undefined ? {} : { input_data: inputData },
    method: "POST"
  });
}

export function getPipelineRun(runId: string): Promise<PipelineRun> {
  return apiRequest<PipelineRun>(`/api/pipeline-runs/${encodeURIComponent(runId)}`);
}

export const api = {
  get: <T>(path: string, options?: ApiRequestOptions) =>
    apiRequest<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: ApiRequestOptions) =>
    apiRequest<T>(path, { ...options, body, method: "POST" }),
  getReports,
  getLatestReport,
  getReport,
  runPipeline,
  getPipelineRun,
  request: apiRequest
};
