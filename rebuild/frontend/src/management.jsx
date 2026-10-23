import { useEffect, useState } from "react";
import { request, hatcheryPath } from "./api";
import { ActionForm, Field, Modal, Badge, ErrorBox } from "./components";
import { timestamp } from "./readings";
export function TankEditor({ hatchery, tank, onClose, onSaved }) {
  const base = hatcheryPath(hatchery, "/tanks");
  return (
    <Modal title={tank ? "Edit tank" : "New tank"} onClose={onClose}>
      <ActionForm
        onSubmit={async (values) => {
          await request(base + (tank ? "/" + tank.id : ""), {
            method: tank ? "PATCH" : "POST",
            body: {
              name: values.name,
              ...(tank ? { expected_version: tank.version } : {}),
            },
          });
          onSaved();
          onClose();
        }}
      >
        <Field
          label="Tank name"
          name="name"
          value={tank?.name}
          maxLength={200}
          required
          autoFocus
        />
      </ActionForm>
      {tank && (
        <ActionForm
          label={tank.archived_at ? "Restore tank" : "Archive tank"}
          onSubmit={async () => {
            await request(
              `${base}/${tank.id}/${tank.archived_at ? "restore" : "archive"}`,
              { method: "POST", body: { expected_version: tank.version } },
            );
            onSaved();
            onClose();
          }}
        >
          <p className="muted">
            Archiving retains history. Unassign every device before archiving.
            Restoring does not restore assignments.
          </p>
        </ActionForm>
      )}
    </Modal>
  );
}
export function DeviceEditor({ hatchery, device, tanks, onClose, onSaved }) {
  const base = hatcheryPath(hatchery, "/devices/" + device.device_id);
  const done = () => {
    onSaved();
    onClose();
  };
  return (
    <Modal title="Manage device" onClose={onClose}>
      <p className="mono">{device.device_id}</p>
      <ActionForm
        onSubmit={async (values) => {
          await request(base, {
            method: "PATCH",
            body: {
              display_name: values.name || null,
              expected_version: device.version,
            },
          });
          done();
        }}
      >
        <Field
          label="Device name"
          name="name"
          value={device.display_name || ""}
          maxLength={200}
        />
      </ActionForm>
      {!device.archived_at && (
        <ActionForm
          label="Save assignment"
          onSubmit={async (values) => {
            await request(base + "/assignment", {
              method: "POST",
              body: {
                tank_id: values.tank || null,
                expected_version: device.version,
              },
            });
            done();
          }}
        >
          <label>
            Assigned tank
            <select name="tank" defaultValue={device.binding?.tank_id || ""}>
              <option value="">Unassigned</option>
              {tanks
                .filter((t) => !t.archived_at)
                .map((t) => (
                  <option value={t.id} key={t.id}>
                    {t.name}
                  </option>
                ))}
            </select>
          </label>
          <p className="muted">
            The device must confirm its new configuration. Old readings keep
            their original tank.
          </p>
        </ActionForm>
      )}
      <ActionForm
        label={device.archived_at ? "Restore device" : "Archive device"}
        onSubmit={async () => {
          await request(
            base + "/" + (device.archived_at ? "restore" : "archive"),
            { method: "POST", body: { expected_version: device.version } },
          );
          done();
        }}
      >
        <p className="muted">
          Unassign before archiving. History and ownership are retained.
        </p>
      </ActionForm>
    </Modal>
  );
}
export function ClaimDevice({ hatchery, tanks, onClose, onSaved }) {
  const [claim, setClaim] = useState(null),
    [error, setError] = useState(null);
  useEffect(() => {
    if (!claim || ["complete", "expired", "cancelled"].includes(claim.state))
      return;
    const abort = new AbortController();
    const timer = setInterval(
      () =>
        request(hatcheryPath(hatchery, "/device-claims/" + claim.id), {
          passive: true,
          signal: abort.signal,
        })
          .then((value) => {
            setClaim(value);
            if (value.state === "complete") onSaved();
          })
          .catch((e) => {
            if (e.name !== "AbortError") setError(e);
          }),
      2500,
    );
    return () => {
      abort.abort();
      clearInterval(timer);
    };
  }, [claim, hatchery, onSaved]);
  return (
    <Modal title="Add device" onClose={onClose}>
      {!claim ? (
        <ActionForm
          label="Start device claim"
          onSubmit={async (values) => {
            setClaim(
              await request(hatcheryPath(hatchery, "/device-claims"), {
                method: "POST",
                body: {
                  device_id: values.device.trim().toUpperCase(),
                  tank_id: values.tank,
                  claim_code: values.code.trim(),
                },
              }),
            );
          }}
        >
          <Field
            name="device"
            label="Device ID"
            placeholder="BB-AABBCC112233"
            pattern="BB-[A-Fa-f0-9]{12}"
            maxLength={15}
            required
            autoFocus
          />
          <Field
            name="code"
            label="Private claim code"
            type="password"
            autoComplete="off"
            minLength={43}
            maxLength={43}
            required
          />
          <label>
            Destination tank
            <select name="tank" required>
              <option value="">Choose a tank</option>
              {tanks
                .filter((t) => !t.archived_at)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
            </select>
          </label>
          <p className="muted">
            Use the private code supplied with a prepared device. Keep the
            device connected so it can prove its identity and confirm the
            assignment.
          </p>
        </ActionForm>
      ) : (
        <div className="claim-progress">
          <Badge>{claim.state.replaceAll("_", " ")}</Badge>
          <p className="mono">{claim.device_id}</p>
          <p>
            {
              {
                pending_proof: "Waiting for the device to prove its identity.",
                awaiting_confirmation:
                  "Assignment saved. Waiting for the device to confirm its configuration.",
                complete: "Device assignment confirmed.",
                expired:
                  "This reservation expired. Close and start a new claim.",
                cancelled: "This claim was cancelled.",
              }[claim.state]
            }
          </p>
          <p className="muted">
            Reservation expires {timestamp(claim.expires_at)}
          </p>
          <ErrorBox error={error} />
          {claim.state === "pending_proof" && (
            <ActionForm
              label="Cancel claim"
              onSubmit={async () =>
                setClaim(
                  await request(
                    hatcheryPath(hatchery, `/device-claims/${claim.id}/cancel`),
                    { method: "POST" },
                  ),
                )
              }
            />
          )}
        </div>
      )}
    </Modal>
  );
}
