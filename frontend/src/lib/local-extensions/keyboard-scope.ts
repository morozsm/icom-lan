let keyboardScope: string | null = null;

export function setLocalExtensionKeyboardScope(scope: string | null): void {
  const next = typeof scope === 'string' && scope.trim() !== '' ? scope : null;
  keyboardScope = next;
}

export function getLocalExtensionKeyboardScope(): string | null {
  return keyboardScope;
}

export function isLocalExtensionKeyboardScopeActive(): boolean {
  return keyboardScope !== null;
}

export function resetLocalExtensionKeyboardScope(): void {
  keyboardScope = null;
}
