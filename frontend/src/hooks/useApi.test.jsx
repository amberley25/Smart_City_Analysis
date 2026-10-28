import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useApi } from "./useApi.js";

describe("useApi", () => {
  it("starts loading, then exposes the data", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 42 });
    const { result } = renderHook(() => useApi(fetcher, []));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ value: 42 });
    expect(result.current.error).toBeNull();
  });

  it("exposes failures and clears stale data", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useApi(fetcher, []));

    await waitFor(() => expect(result.current.error?.message).toBe("boom"));
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("refetches when a dependency changes and keeps old data meanwhile", async () => {
    let resolveSecond;
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce("first")
      .mockImplementationOnce(() => new Promise((resolve) => (resolveSecond = resolve)));
    const { result, rerender } = renderHook(({ zone }) => useApi(fetcher, [zone]), { initialProps: { zone: "a" } });
    await waitFor(() => expect(result.current.data).toBe("first"));

    rerender({ zone: "b" });
    await waitFor(() => expect(result.current.loading).toBe(true));
    expect(result.current.data).toBe("first");

    await act(async () => resolveSecond("second"));
    expect(result.current.data).toBe("second");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("reload() runs the fetcher again", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce("a").mockResolvedValueOnce("b");
    const { result } = renderHook(() => useApi(fetcher, []));
    await waitFor(() => expect(result.current.data).toBe("a"));

    act(() => result.current.reload());

    await waitFor(() => expect(result.current.data).toBe("b"));
  });

  it("aborts the request on unmount and ignores the abort error", async () => {
    let signal;
    const fetcher = vi.fn((s) => {
      signal = s;
      return new Promise((_, reject) => s.addEventListener("abort", () => reject(Object.assign(new Error("x"), { name: "AbortError" }))));
    });
    const { result, unmount } = renderHook(() => useApi(fetcher, []));

    unmount();

    expect(signal.aborted).toBe(true);
    expect(result.current.error).toBeNull();
  });
});
