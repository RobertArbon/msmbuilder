#include <emmintrin.h>
#include "logsumexp.h"
#include "float.h"
#include <stdio.h>
#include <math.h>
#include "sse_mathfun.h"

float logsumexp2(float v1, float v2) {
    float max = (((v1) > (v2)) ? (v1) : (v2));
    return log(exp(v1-max) + exp(v2-max)) + max;
}


float logsumexp(const float* __restrict__ buf, int N) {
    int i;
    int nu = (( N >> 2 ) << 2 );
    float* StX = buf + nu;
    float sum = 0;
    float mymax = 0;
    float* X;
    float max4[4] __attribute__((aligned(16))) = {0};
    __m128 _v;
    __m128 _m;

    if (N == 1)
        return buf[0];
    if (N == 2) {
        mymax = fmaxf(buf[0], buf[1]);
        return log(exp(buf[0] - mymax) + exp(buf[1] - mymax)) + mymax;
    } if (N == 3) {
        mymax = fmaxf(fmaxf(buf[0], buf[1]), buf[2]);
        return log(exp(buf[0] - mymax) + exp(buf[1] - mymax) + exp(buf[2] - mymax)) + mymax;
    }
    

    if (N > 0) {
        X = buf;
        if (nu != 0) {
            StX = buf + nu;
            _v = _mm_loadu_ps(X);
            X += 4;
            while (X != StX) {
                _v = _mm_max_ps(_v, _mm_loadu_ps(X));
                X += 4;
            }

            _mm_store_ps(max4, _v);
            mymax = fmaxf(fmaxf(fmaxf(max4[0], max4[1]), max4[2]), max4[3]);
        }
        for(i = N - nu; i != 0; i--)
            mymax = fmaxf(mymax, X[i]);
        
        X = buf;
        if (nu != 0) {
            StX = X + nu;
            _m = _mm_load1_ps(&mymax);
            _v = exp_ps(_mm_sub_ps(_mm_loadu_ps(X), _m));
            X += 4;
            while (X != StX) {
                _v = _mm_add_ps(_v, exp_ps(_mm_sub_ps(_mm_loadu_ps(X), _m)));
                X += 4;
            }

            // horizontal add
            _v = _mm_add_ps(_v, _mm_movehl_ps(_v, _v));
            _v = _mm_add_ss(_v, _mm_shuffle_ps(_v, _v, 1));
            _mm_store_ss(&sum, _v);
        }
        for(i = N - nu; i != 0; i--)
            sum += expf(X[i] - mymax);
    }

    return log(sum) + mymax;
}


float _mm_logsumexp(__m128* buf, int N) {
    int i;
    float sum = 0;
    float mymax = 0;
    float max4[4] __attribute__((aligned(16))) = {0};

    __m128 _v;
    __m128 _m;

    _v = buf[0];
    for (i = 1; i < N; i++)
        _v = _mm_max_ps(_v, buf[i]);

    _mm_store_ps(max4, _v);
    mymax = fmaxf(fmaxf(fmaxf(max4[0], max4[1]), max4[2]), max4[3]); 

    _m = _mm_load1_ps(&mymax);
    _v = exp_ps(_mm_sub_ps(buf[0], _m));
    for (i = 1; i < N; i++)
        _v = _mm_add_ps(_v, exp_ps(_mm_sub_ps(buf[i], _m)));

    // horizontal add
    _v = _mm_add_ps(_v, _mm_movehl_ps(_v, _v));
    _v = _mm_add_ss(_v, _mm_shuffle_ps(_v, _v, 1));
    _mm_store_ss(&sum, _v);

    return log(sum) + mymax;
}

/*int main() {
    float buf[33];
    for (int i = 0; i < 33; i++)
        buf[i] = pow(2.0, -i);
    printf("logsumexp = %f\n", logsumexp(buf, 32));


    __m128 bufv[8];
    for (int i = 0; i < 8; i++)
        bufv[i] = _mm_loadu_ps(buf + 4*i);
    printf("logsumexp = %f\n", _mm_logsumexp(bufv, 8));

    return 1;    
}
*/
