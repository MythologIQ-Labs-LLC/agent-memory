#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
static SHA_CTX base; static volatile int found = 0; static char result[17];
static void *work(void *arg) {
  unsigned long long t = (unsigned long long)(size_t)arg; char tail[18]; unsigned char md[20];
  for (unsigned long long i = 0; !found; i++) {
    unsigned long long n = (i << 2) | t;
    snprintf(tail, sizeof tail, "%016llx\n", n);
    SHA_CTX c = base; SHA1_Update(&c, tail, 17); SHA1_Final(md, &c);
    if (md[0] == 0x74 && md[1] == 0x5f && md[2] == 0x78 && md[3] == 0x9c) { memcpy(result, tail, 16); result[16] = 0; found = 1; }
  }
  return NULL;
}
int main(void) {
  FILE *f = fopen("prefix.txt", "rb"); fseek(f, 0, SEEK_END); long n = ftell(f); rewind(f);
  char *buf = malloc(n); fread(buf, 1, n, f); fclose(f);
  char hdr[64]; int h = snprintf(hdr, sizeof hdr, "blob %ld", n + 17); /* content = prefix + 16 hex + \n */
  SHA1_Init(&base); SHA1_Update(&base, hdr, h + 1); SHA1_Update(&base, buf, n);
  pthread_t th[4]; for (long i = 0; i < 4; i++) pthread_create(&th[i], NULL, work, (void *)i);
  for (int i = 0; i < 4; i++) pthread_join(th[i], NULL);
  printf("%s\n", result); return 0;
}
