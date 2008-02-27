# daemon code from ASPN

import os


def daemonize(pidfile, home):
    """
    Detach this process from the controlling terminal and run it in the
    background as a daemon.
    """

    UMASK = 0
    WORKDIR = "/"
    REDIRECT_TO = getattr(os, 'devnull', '/dev/null')
    MAXFD = 1024

    try:
        pid = os.fork()
    except OSError, e:
        raise Exception("%s [%d]" % (e.strerror, e.errno))

    if (pid == 0):      # The first child.
        os.setsid()

        try:
            pid = os.fork()     # Fork a second child.
        except OSError, e:
            raise Exception, "%s [%d]" % (e.strerror, e.errno)

        if (pid == 0):  # The second child.
            os.chdir(WORKDIR)
            os.umask(UMASK)
        else:
            os._exit(0) # Exit parent (the first child) of the second child.
    else:
        os._exit(0)     # Exit parent of the first child.

    #import resource            # Resource usage information.
    #maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    #if (maxfd == resource.RLIM_INFINITY):
    #    maxfd = MAXFD

    # Iterate through and close all file descriptors.
    #for fd in range(3, maxfd):
    #    try:
    #        os.close(fd)
    #    except OSError:        # ERROR, fd wasn't open to begin with (ignored)
    #        pass

    # This call to open is guaranteed to return the lowest file descriptor,
    # which will be 0 (stdin), since it was closed above.
    #os.open(REDIRECT_TO, os.O_RDWR)    # standard input (0)

    # Duplicate standard input to standard output and standard error.
    #os.dup2(0, 1)                      # standard output (1)
    #os.dup2(0, 2)                      # standard error (2)

    f = open(pidfile, 'w')
    f.write('%d\n' % (os.getpid(),))
    f.write('%s\n' % (home,))
    f.close()


def is_running(pidfile):
    try:
        f = open(pidfile, 'r')
    except IOError:
        return False
    pid = int(f.readline())
    f.close()
    try:
        os.kill(pid, 0)
    except OSError:
        # no such process
        return False
    return True
