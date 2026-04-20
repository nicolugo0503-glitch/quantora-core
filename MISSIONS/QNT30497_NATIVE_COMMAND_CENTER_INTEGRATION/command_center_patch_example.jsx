// QNT30497 — Example native patch
// This is an example only. It is not automatically applied.
// Use it to wire the buttons into the real command center source.

import React, { useEffect, useRef } from "react";
import { mountQNT30497MissionButtons } from "./native_mount_helper.js";

export default function CommandCenterMissionHubPatchExample() {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current) return;
    if (mountRef.current.dataset.mounted === "true") return;

    mountQNT30497MissionButtons(mountRef.current, {
      title: "Conversation Missions",
      subtitle: "QNT30484–QNT30495",
      basePath: "",
    });

    mountRef.current.dataset.mounted = "true";
  }, []);

  return (
    <div style={{ marginTop: 12 }}>
      <div ref={mountRef} />
    </div>
  );
}
