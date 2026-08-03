// This file can be replaced during build by using the `fileReplacements` array.
// `ng build` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.

export const environment = {
  production: false,
  // Base URL of the RAG backend API. The chat endpoint is expected at `${apiUrl}/chat`.
  apiUrl: 'http://localhost:8000/api',
  // When true, the UI runs against a built-in mock so it works before the
  // RAG backend exists. Flip to false once the API is available.
  useMock: false
};

/*
 * For easier debugging in development mode, you can import the following file
 * to ignore zone related error stack frames such as `zone.run`, `zoneDelegate.invokeTask`.
 *
 * This import should be commented out in production mode because it will have a negative impact
 * on performance if an error is thrown.
 */
// import 'zone.js/plugins/zone-error';  // Included with Angular CLI.
