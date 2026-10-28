import { describe, expect, it } from "vitest";
import { dateTime, num, parseTime, percent, shortDate, signedPercent, toInputValue } from "./format.js";

describe("number formatting", () => {
  it("groups thousands and fixes decimals", () => {
    expect(num(1234.567, 1)).toBe("1,234.6");
    expect(num(35029.41, 0)).toBe("35,029");
  });

  it("shows a dash for missing values instead of NaN or null", () => {
    for (const value of [null, undefined, NaN]) {
      expect(num(value)).toBe("—");
      expect(percent(value)).toBe("—");
      expect(signedPercent(value)).toBe("—");
    }
  });

  it("keeps zero as a real value", () => {
    expect(num(0, 1)).toBe("0.0");
  });

  it("signs changes with a true minus sign", () => {
    expect(signedPercent(2.25, 1)).toBe("+2.3%");
    expect(signedPercent(-2.2)).toBe("−2.2%");
    expect(signedPercent(0)).toBe("0.0%");
  });
});

describe("timestamps", () => {
  it("treats naive API timestamps as UTC regardless of the viewer's time zone", () => {
    expect(parseTime("2026-04-30T23:00:00").toISOString()).toBe("2026-04-30T23:00:00.000Z");
    expect(parseTime("2026-04-30").toISOString()).toBe("2026-04-30T00:00:00.000Z");
  });

  it("respects an explicit offset", () => {
    expect(parseTime("2026-04-30T23:00:00+02:00").toISOString()).toBe("2026-04-30T21:00:00.000Z");
    expect(parseTime("2026-04-30T23:00:00Z").toISOString()).toBe("2026-04-30T23:00:00.000Z");
  });

  it("renders dates and times in UTC", () => {
    expect(shortDate("2026-04-30")).toBe("30 Apr");
    expect(dateTime("2026-04-30T23:00:00")).toBe("30 Apr 2026, 23:00");
  });

  it("produces the value a datetime-local input expects", () => {
    expect(toInputValue("2026-04-20T13:00:00")).toBe("2026-04-20T13:00");
  });
});
