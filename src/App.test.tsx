import { render, screen } from '@testing-library/react';
import App, { detectColumnMapping, normalizeHeader } from './App';
import { describe, expect, it } from 'vitest';

describe('normalizeHeader', () => {
  it('normalizes messy header names into comparable values', () => {
    expect(normalizeHeader('First Name')).toBe('first name');
    expect(normalizeHeader('E-Mail Address')).toBe('e mail address');
    expect(normalizeHeader('  Last__Name  ')).toBe('last name');
  });
});

describe('detectColumnMapping', () => {
  it('matches canonical columns to common layout aliases', () => {
    const mapping = detectColumnMapping([
      'First Name',
      'Surname',
      'E-mail address',
      'Cell Phone',
      'Employer',
      'State/Province',
    ]);

    expect(mapping.firstName).toBe('First Name');
    expect(mapping.lastName).toBe('Surname');
    expect(mapping.email).toBe('E-mail address');
    expect(mapping.phone).toBe('Cell Phone');
    expect(mapping.company).toBe('Employer');
    expect(mapping.state).toBe('State/Province');
  });

  it('returns null for unmapped columns', () => {
    const mapping = detectColumnMapping(['Name', 'Notes', 'Comments']);
    expect(mapping.firstName).toBeNull();
    expect(mapping.lastName).toBeNull();
    expect(mapping.email).toBeNull();
  });
});

describe('App', () => {
  it('renders upload interface and mapping controls when a file is selected', async () => {
    render(<App />);

    expect(screen.getByText('Excel Upload and Select')).toBeInTheDocument();
    expect(screen.getByLabelText('Choose Excel file')).toBeInTheDocument();
  });
});
