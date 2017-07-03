from mpfmc.core.audio.sdl2 cimport *

# ---------------------------------------------------------------------------
#    Inline functions
# ---------------------------------------------------------------------------

cdef inline Uint8 lerpU8(float progress, Uint8 a, Uint8 b) nogil:
    """
    Linearly interpolate between 2 8-bit values.
    Args:
        progress: Progress (0.0 to 1.0) between the two values
        a: First 8-bit value
        b: Second 8-bit value

    Returns:
        New 8-bit value between the supplied values
    """
    return <Uint8> ((1.0 - progress) * a + progress * b)

cdef inline float in_out_quad(float progress) nogil:
    """
    A quadratic easing function used for smoother audio fading
    Args:
        progress: 0.0 to 1.0

    Notes:
        At 0.0 the output is 0.0 and at 1.0 the output is 1.0.
    """
    cdef float p
    p = progress * 2
    if p < 1:
        return 0.5 * p * p
    p -= 1.0
    return -0.5 * (p * (p - 2.0) - 1.0)

