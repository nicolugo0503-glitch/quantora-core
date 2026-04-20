// QNT30498 — Drop-in Command Center Patch
// Additive only. No existing core files modified.
//
// PURPOSE
// A ready-to-drop React component that mounts the QNT30497 conversation mission buttons
// inside the existing Quantora command center.

import React, { useEffect, useRef } from "react";
import { mountQNT30497MissionButtons } from "../QNT30497_NATIVE_COMMAND_CENTER_INTEGRATION/native_mount_helper.js";

export default function QuantoraConversationMissionButtons() {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current) return;
    if (mountRef.current.dataset.qnt30498Mounted === "true") return;

    mountQNT30497MissionButtons(mountRef.current, {
      title: "Conversation Missions",
      subtitle: "QNT30484–QNT30495",
      basePath: "",
    });

    mountRef.current.dataset.qnt30498Mounted = "true";
  }, []);

  return (
    <div
      style={{
        marginTop: 12,
        width: "100%",
      }}
    >
      <div ref={mountRef} />
    </div>
  );
}
