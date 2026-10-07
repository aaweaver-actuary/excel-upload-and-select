import '@testing-library/jest-dom/vitest';
import { TextEncoder } from 'node:util';

globalThis.TextEncoder = TextEncoder;
