import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { BaseHeader } from './base/BaseHeader';
import { BaseSubheader } from './base/BaseSubheader';
import { BaseDetailHeader } from './base/BaseDetailHeader';
import { BaseButton } from './base/BaseButton';
import { BaseOption } from './base/BaseOption';
import { BaseLink } from './base/BaseLink';
import { Disclosure } from './shared/Disclosure';
import { LabeledSelect } from './shared/LabeledSelect';
import buttonStyles from './base/BaseButton.module.css';
import headerStyles from './base/BaseHeader.module.css';

afterEach(cleanup);

it('preserves heading levels, native attributes, children and caller classes', () => {
  render(<>
    <BaseHeader id="title" className="custom-title" aria-describedby="description">Page title</BaseHeader>
    <BaseSubheader>Section title</BaseSubheader>
    <BaseDetailHeader>Detail title</BaseDetailHeader>
  </>);
  const heading = screen.getByRole('heading', { level: 1, name: 'Page title' });
  expect(heading).toHaveAttribute('id', 'title');
  expect(heading).toHaveAttribute('aria-describedby', 'description');
  expect(heading).toHaveClass(headerStyles.element, 'custom-title');
  expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Section title');
  expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Detail title');
});

it('preserves button variants, native attributes, events and disabled behavior', async () => {
  const onClick = vi.fn();
  const view = render(<BaseButton variant="primary" className="custom-button" type="submit" title="Submit import" disabled onClick={onClick}>Process</BaseButton>);
  const button = screen.getByRole('button', { name: 'Process' });
  expect(button).toHaveClass(buttonStyles.element, buttonStyles.primary, 'custom-button');
  expect(button).toHaveAttribute('type', 'submit');
  expect(button).toHaveAttribute('title', 'Submit import');
  expect(button).not.toHaveAttribute('variant');
  await userEvent.click(button);
  expect(onClick).not.toHaveBeenCalled();
  view.rerender(<BaseButton type="button" onClick={onClick}>Process</BaseButton>);
  await userEvent.click(screen.getByRole('button', { name: 'Process' }));
  expect(onClick).toHaveBeenCalledTimes(1);
});

it('preserves select labels, options, native attributes and change events', async () => {
  const onChange = vi.fn();
  render(<LabeledSelect label="Worksheet " name="sheet" aria-describedby="sheet-help" defaultValue="first" onChange={onChange}>
    <BaseOption value="first">First sheet</BaseOption>
    <BaseOption value="second">Second sheet</BaseOption>
  </LabeledSelect>);
  const select = screen.getByRole('combobox', { name: 'Worksheet' });
  expect(select).toHaveAttribute('name', 'sheet');
  expect(select).toHaveAttribute('aria-describedby', 'sheet-help');
  await userEvent.selectOptions(select, 'second');
  expect(select).toHaveValue('second');
  expect(onChange).toHaveBeenCalledTimes(1);
});

it('preserves native disclosure and download-link attributes', async () => {
  render(<Disclosure summary="Details" open id="details">
    <BaseLink href="/result" download="result.xlsx">Download</BaseLink>
  </Disclosure>);
  const summary = screen.getByText('Details');
  expect(summary.parentElement).toHaveAttribute('open');
  expect(summary.parentElement).toHaveAttribute('id', 'details');
  expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute('download', 'result.xlsx');
  await userEvent.click(summary);
  expect(summary.parentElement).not.toHaveAttribute('open');
});
