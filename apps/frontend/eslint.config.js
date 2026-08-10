import { baseConfig } from "@vault/config/typescript/eslint.config.mjs";

export default [
  { ignores: ["dist", "src/routeTree.gen.ts"] },
  ...baseConfig,
  {
    languageOptions: {
      ecmaVersion: 2022,
      globals: { window: "readonly", document: "readonly" },
    },
  },
  {
    // TanStack Router's file-based convention exports both `Route` and a
    // component from the same file — a false positive for this rule.
    files: ["src/routes/**/*.tsx"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
];
