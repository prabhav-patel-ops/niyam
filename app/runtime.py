"""Operator-owned configuration and public, non-sensitive readiness state."""
import os
from urllib.parse import urlsplit
from . import data

PRICE_BASIS = 'split_bonus_adjusted_ex_dividend'


def production():
    return os.getenv('NIYAM_ENV', 'development') == 'production'


def price_basis_confirmed():
    return os.getenv('NIYAM_PRICE_BASIS', '') == PRICE_BASIS


def validate_config():
    if os.getenv('NIYAM_ENV', 'development') not in {'development', 'production'}:
        raise ValueError('NIYAM_ENV must be development or production.')
    if production():
        url = urlsplit(os.getenv('NIYAM_PUBLIC_URL', ''))
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {'', '/'}:
            raise ValueError('Production requires NIYAM_PUBLIC_URL as an HTTPS origin.')
        if '*' in os.getenv('NIYAM_ALLOWED_HOSTS', ''):
            raise ValueError('Production does not allow wildcard hosts.')
    for key in ['LLM_BASE_URL', 'DAILY_FEED_URL']:
        value = os.getenv(key, '').strip()
        if not value:
            continue
        url = urlsplit(value)
        local = url.scheme == 'http' and url.hostname in {'localhost', '127.0.0.1', '::1'}
        if not url.hostname or url.username or url.password or url.fragment or (url.scheme != 'https' and not local):
            raise ValueError(f'{key} must use HTTPS, or loopback HTTP, without embedded credentials.')
    basis = os.getenv('NIYAM_PRICE_BASIS', '')
    if basis and basis != PRICE_BASIS:
        raise ValueError('NIYAM_PRICE_BASIS does not match the supported price-return model.')


def public_state():
    catalog = data.catalog()
    ai = bool(os.getenv('LLM_BASE_URL') and os.getenv('LLM_MODEL'))
    research = catalog['ready'] and price_basis_confirmed()
    return {'research_ready': research, 'interpretation_ready': ai,
            'ready': research and ai,
            'message': 'The workspace is ready.' if research and ai else 'The research service is being prepared. Please try again shortly.'}


def prepare_strategy(strategy):
    # The operator attests to the installed dataset; a browser cannot override it.
    return strategy.model_copy(update={'price_basis_confirmed': price_basis_confirmed()})


def user_catalog():
    value = data.catalog()
    return {k: v for k, v in value.items() if k not in {'folders', 'errors'}}
