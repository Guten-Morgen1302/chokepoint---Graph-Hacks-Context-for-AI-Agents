import { loadFont as loadDisplay } from "@remotion/google-fonts/BricolageGrotesque";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

export const display = loadDisplay("normal", { weights: ["400", "600", "800"], subsets: ["latin"] }).fontFamily;
export const mono = loadMono("normal", { weights: ["400", "700"], subsets: ["latin"] }).fontFamily;

export const C = {
  bg: "#0a0c12",
  bg2: "#111522",
  panel: "#161a27",
  line: "#2a3042",
  text: "#f2f4f8",
  muted: "#98a0b3",
  accent: "#5b7cff", // cobalt, the app's own cut colour: the one accent
  accentSoft: "#93a8ff",
  jewel: "#ff5c61", // crown jewels, exactly as red as in the app
  green: "#3ddc84",
  warn: "#ffb547",
};

export const END_URL = "github.com/Guten-Morgen1302/chokepoint";

export const FPS = 30;
export const s = (seconds: number) => Math.round(seconds * FPS);
