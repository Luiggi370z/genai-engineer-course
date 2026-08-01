import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

/** The shipped deliverable has always been called course.html; keep that name. */
function emitAsCourseHtml(): Plugin {
  return {
    name: "emit-course-html",
    enforce: "post",
    generateBundle(_options, bundle) {
      const entry = bundle["index.html"];
      if (entry) entry.fileName = "course.html";
    },
  };
}

// The deliverable is one self-contained HTML file a student can open from disk,
// so everything (JS + CSS) is inlined and no assets are emitted alongside it.
export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile(), emitAsCourseHtml()],
  build: {
    target: "es2022",
    cssCodeSplit: false,
    assetsInlineLimit: Number.MAX_SAFE_INTEGER,
    chunkSizeWarningLimit: 2000,
  },
});
