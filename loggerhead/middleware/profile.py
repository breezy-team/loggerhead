'''Profiling middleware for paste.'''
from paste.debug.profile import ProfileMiddleware

class CProfileMiddleware(ProfileMiddleware):
    '''Paste middleware for profiling with cProfile.'''
