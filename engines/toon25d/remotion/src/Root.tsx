import React from "react";
import { Composition } from "remotion";
import { BridgeShort, BRIDGE_FRAMES } from "./videos/bridge/Bridge";

// toon25d spike: the upstream bridge short, unchanged (see docs/superpowers/specs/2026-11-05-style-toon25d.md).
export const Root: React.FC = () => (
  <Composition id="BridgeShort" component={BridgeShort} durationInFrames={BRIDGE_FRAMES} fps={30} width={1080} height={1920} />
);
