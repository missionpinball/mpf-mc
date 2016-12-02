#include <SDL.h>
/*
SDL audio buffer conversion function. Converts an audio buffer of one format into another buffer with the desired
format.  Code based on the SDL_Mixer library function Mix_LoadWAV_RW (https://www.libsdl.org/projects/SDL_mixer/).

Note: This code exists because no way was discovered to get the SDL_BuildAudioCVT function to work in Cython.
*/
static int convert_audio_to_desired_format(SDL_AudioSpec input_spec, SDL_AudioSpec desired_spec, Uint8* input_buffer, Uint32 input_size, Uint8** output_buffer, Uint32 *output_size)
{
    SDL_AudioCVT cvt;
    int return_value;
    int sample_size;

    /* Build the audio converter */
    return_value = SDL_BuildAudioCVT(&cvt, input_spec.format, input_spec.channels, input_spec.freq,
        desired_spec.format, desired_spec.channels, desired_spec.freq);
    if (return_value < 0)
        return (return_value);

    /* Create the conversion buffers.  Do not forget to free these when finished with them. */
    sample_size = (SDL_AUDIO_BITSIZE(input_spec.format) / 8) * input_spec.channels;
    cvt.len = input_size & ~(sample_size-1);
    cvt.buf = (Uint8 *)SDL_calloc(1, cvt.len * cvt.len_mult);
    if (cvt.buf == NULL) {
        SDL_SetError("Out of memory");
        return (-1);
    }

    /* Copy the input sample data to the conversion buffer */
    SDL_memcpy(cvt.buf, input_buffer, input_size);

    /* Run the audio converter */
    return_value = SDL_ConvertAudio(&cvt);
    if (return_value < 0 ) {
        SDL_free(cvt.buf);
        return (return_value);
    }

    /* Return the converted audio data (reallocate output buffer in case it got smaller as
       a result of conversion). */
    *output_buffer = SDL_realloc(cvt.buf, cvt.len_cvt);
    *output_size = cvt.len_cvt;

    return 1;
}
