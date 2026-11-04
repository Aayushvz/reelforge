import { Config } from "@remotion/cli/config";

// three.js needs a real GPU: ANGLE uses the D3D11 backend on Windows.
Config.setChromiumOpenGlRenderer("angle");
Config.setVideoImageFormat("jpeg");
