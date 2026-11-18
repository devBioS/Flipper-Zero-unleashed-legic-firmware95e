/* Hardware-independent reference vectors from the PR's NFC unit tests. */
#include <assert.h>
#include <stdio.h>
#include <nfc/protocols/legic_prime/legic_prime_crc.h>
#include <nfc/protocols/legic_prime/legic_prime_prng.h>

static uint32_t keystream(uint8_t iv, int skip, uint8_t bits) {
    legic_prime_prng_init(iv);
    legic_prime_prng_forward(skip);
    uint32_t value = 0;
    for(uint8_t i = 0; i < bits; ++i) {
        value |= (uint32_t)legic_prime_prng_get_bit() << i;
        legic_prime_prng_forward(1);
    }
    return value;
}

int main(void) {
    assert(keystream(0x55, 0, 32) == 0x82B50098);
    assert(keystream(0x01, 0, 32) == 0xAA13D912);
    assert(keystream(0x7F, 0, 32) == 0x3D7AD81F);
    assert(keystream(0x55, 100, 16) == 0x0093);
    assert(keystream(0, 0, 32) == 0);
    assert(legic_prime_crc8((const uint8_t*)"123456789", 9) == 0xC6);
    const uint8_t uids[][4] = {{0x81, 0xAB, 0x2C, 0x87}, {0x11, 0x22, 0x33, 0x44}, {0xA1, 0xB2, 0xC3, 0xD4}};
    const uint8_t expected[] = {0x2D, 0xD4, 0xFD};
    for(size_t i = 0; i < 3; ++i) assert(legic_prime_crc8(uids[i], 4) == expected[i]);
    assert(legic_prime_crc4(11, 9, 0x2D) == 4);
    assert(legic_prime_crc4(1, 6, 0x81) == 3);
    assert(legic_prime_crc4(1200, 11, 0xA1) == 7);
    assert(legic_prime_crc4(2046, 11, 0xA5) == 0xD);
    puts("PASS: 13 LEGIC PRNG/CRC reference vectors (host; no RF timing test)");
}
