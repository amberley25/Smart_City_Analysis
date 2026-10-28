import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { api } from "../../api.js";
import ZoneProvider from "../../components/ZoneProvider.jsx";
import AnomalyCheck from "./AnomalyCheck.jsx";

const flagged = {
  anomaly: true,
  classification: "Anomalous",
  score: 0.68,
  threshold: 0.62,
  expected_kwh: 452,
  reasons: ["Metered energy disagrees with V x I x pf by 36% (possible meter fault)"],
  signals: { profile_z: 10.1, log_ratio: 0.43, power_balance: -0.36, voltage_dev: 0, power_factor: 0.95 },
};

const setup = () =>
  render(
    <ZoneProvider>
      <AnomalyCheck />
    </ZoneProvider>,
  );

describe("AnomalyCheck", () => {
  it("submits numeric readings and shows the verdict with its reasons", async () => {
    const check = vi.spyOn(api, "checkAnomaly").mockResolvedValue(flagged);
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole("button", { name: "Meter mismatch" }));
    await user.click(screen.getByRole("button", { name: "Check reading" }));

    expect(check).toHaveBeenCalledWith(
      expect.objectContaining({ zone: "Downtown", energy_kwh: 690, voltage_v: 399, current_a: 670, power_factor: 0.95 }),
    );
    expect(await screen.findByText("Anomalous")).toBeInTheDocument();
    expect(screen.getByText(/possible meter fault/)).toBeInTheDocument();
  });

  it("sends an emptied field as null so the API can name it", async () => {
    const check = vi.spyOn(api, "checkAnomaly").mockRejectedValue(new Error("energy_kwh is required"));
    const user = userEvent.setup();
    setup();

    await user.clear(screen.getByLabelText(/Energy/));
    await user.click(screen.getByRole("button", { name: "Check reading" }));

    expect(check).toHaveBeenCalledWith(expect.objectContaining({ energy_kwh: null }));
    expect(await screen.findByRole("alert")).toHaveTextContent("energy_kwh is required");
  });

  it("disables the button while a request is in flight", async () => {
    let finish;
    vi.spyOn(api, "checkAnomaly").mockReturnValue(new Promise((resolve) => (finish = resolve)));
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole("button", { name: "Check reading" }));

    expect(screen.getByRole("button", { name: "Scoring…" })).toBeDisabled();
    finish(flagged);
    expect(await screen.findByText("Anomalous")).toBeInTheDocument();
  });
});
