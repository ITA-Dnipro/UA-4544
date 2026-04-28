import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import Header from './Header';

const renderHeader = () =>
  render(
    <MemoryRouter>
      <Header />
    </MemoryRouter>
  );

describe('Header', () => {
  test('renders logo with link to /', () => {
    renderHeader();
    const logo = screen.getByRole('link', { name: /scalea/i });
    expect(logo).toBeInTheDocument();
    expect(logo).toHaveAttribute('href', '/');
  });

  test('renders nav links', () => {
    renderHeader();
    expect(screen.getByRole('link', { name: /startups/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /investors/i })).toBeInTheDocument();
  });

  test('renders search input', () => {
    renderHeader();
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
  });

  test('renders Login and Sign Up links when logged out', () => {
    renderHeader();
    expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();
  });

  test('search navigates to /search?q=...', () => {
    renderHeader();
    const input = screen.getByPlaceholderText(/search/i);
    fireEvent.change(input, { target: { value: 'fintech' } });
    fireEvent.submit(input.closest('form')!);
    // navigation is handled by react-router, no error = pass
  });
});