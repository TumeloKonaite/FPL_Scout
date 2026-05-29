import { ApiError } from "@/src/lib/api";

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const detail = error.detail;
    if (
      detail &&
      typeof detail === "object" &&
      "detail" in detail &&
      typeof detail.detail === "string"
    ) {
      return detail.detail;
    }

    return `${error.status} ${error.statusText}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong.";
}
