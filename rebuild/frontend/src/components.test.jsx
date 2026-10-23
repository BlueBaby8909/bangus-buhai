import { it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ActionForm, Field, Modal, MetricStrip } from "./components";
it("labels inputs and surfaces failed submissions for retry", async () => {
  const submit = vi.fn().mockRejectedValue({ code: "stale_version" }),
    user = userEvent.setup();
  render(
    <ActionForm onSubmit={submit}>
      <Field label="Tank name" name="name" required />
    </ActionForm>,
  );
  await user.type(screen.getByLabelText("Tank name"), "Nursery");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(submit).toHaveBeenCalledWith({ name: "Nursery" });
  expect(await screen.findByRole("alert")).toHaveTextContent("Refresh");
  expect(screen.getByRole("button")).toBeEnabled();
});
it("uses a native modal and restores focus", async () => {
  const button = document.createElement("button");
  document.body.appendChild(button);
  button.focus();
  const { unmount } = render(
    <Modal title="Edit tank" onClose={() => {}}>
      <p>Editor</p>
    </Modal>,
  );
  expect(screen.getByRole("dialog")).toHaveAttribute("open");
  unmount();
  await waitFor(() => expect(document.activeElement).toBe(button));
  button.remove();
});
it("shows absence without fabricated metrics", () => {
  render(<MetricStrip />);
  expect(screen.getAllByText("No reading")).toHaveLength(3);
  expect(screen.getByText(/No delivery yet/)).toBeInTheDocument();
});
