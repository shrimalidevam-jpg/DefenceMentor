/// <reference types="vite/client" />

interface GoogleCredentialResponse {
	credential: string
}

interface GoogleIdentityConfiguration {
	client_id: string
	callback: (response: GoogleCredentialResponse) => void
	auto_select?: boolean
}

interface GoogleIdentityApi {
	initialize: (configuration: GoogleIdentityConfiguration) => void
	renderButton: (parent: HTMLElement, options: { theme: string; size: string; width: number; text: string; shape: string }) => void
}

interface Window {
	google?: { accounts: { id: GoogleIdentityApi } }
}
