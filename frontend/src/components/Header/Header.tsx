import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import styles from './Header.module.css';
import logoSvg from '../../assets/logo.svg';

const Header = () => {
  const navigate = useNavigate();
  const [searchValue, setSearchValue] = useState('');

  const isAuthenticated = false;

  const handleSearchSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const trimmedValue = searchValue.trim();
    navigate(`/search?q=${encodeURIComponent(trimmedValue)}`);
  };

  return (
    <header className={styles.header}>
      <div className={styles.headerContainer}>
        <div className={styles.left}>
          <Link to="/" className={styles.logo}>
            <img src={logoSvg} alt="Scalea logo" className={styles.logoIcon} />
            <span className={styles.logoText}>SCALEA</span>
          </Link>
        </div>

        <div className={styles.center}>
          <nav className={styles.nav}>
            <Link to="/startups" className={styles.navLink}>
              Startups
            </Link>

            <Link to="/investors" className={styles.navLink}>
              Investors
            </Link>
          </nav>
        </div>

        <div className={styles.right}>
          <form className={styles.searchForm} onSubmit={handleSearchSubmit}>
            <input
              type="text"
              placeholder="Search"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              className={styles.searchInput}
            />

            <button
              type="submit"
              className={styles.searchButton}
              aria-label="search"
            >
              🔎
            </button>
          </form>

          {isAuthenticated ? (
            <div className={styles.userBlock}>
              <Link to="/profile" className={styles.profileLink}>
                My Profile
              </Link>

              <button type="button" className={styles.logoutButton}>
                Log Out
              </button>
            </div>
          ) : (
            <div className={styles.auth}>
              <Link to="/login" className={styles.loginLink}>
                Login
              </Link>

              <Link to="/register" className={styles.registerButton}>
                Sign Up
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;