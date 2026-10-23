#include <string.h>
#include "unity.h"
#include "device_setup.h"
#include "telemetry.h"
#include "t13a_fixture.h"
#include "cJSON.h"
#include "mbedtls/base64.h"
#include "mbedtls/pk.h"
#include "psa/crypto.h"

extern void t13a_reset_nvs(void);
extern void t13a_fail_write(int boundary, bool after);
extern void run_t13a_queue_tests(void);
static const char *DEVICE = "BB-14C19FC68C60";

static void test_t13a_configuration_digest_and_strict_fields(void)
{
    const char *booleans = "{\"archived\":false,\"confirmed\":true,\"binding\":null,\"revision\":1}";
    cJSON *valid = telemetry_parse_json(booleans, strlen(booleans), true);
    TEST_ASSERT_NOT_NULL(valid); cJSON_Delete(valid);
    const char *invalid[] = {"{\"revision\":1.0}", "{\"revision\":1e0}", "{\"revision\":1E+0}",
        "{\"revision\":.1}", "{\"revision\":+1}", "{\"revision\":01}"};
    for (unsigned i = 0; i < sizeof(invalid)/sizeof(invalid[0]); ++i) {
        TEST_ASSERT_NULL(telemetry_parse_json(invalid[i], strlen(invalid[i]), true));
    }
    device_setup_config_t value;
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_parse(T13A_PENDING, strlen(T13A_PENDING), DEVICE, &value));
    TEST_ASSERT_EQUAL(1, value.revision); TEST_ASSERT_EQUAL(0, value.confirmed);
    TEST_ASSERT_NOT_EQUAL(ESP_OK, device_setup_parse(T13A_PENDING, strlen(T13A_PENDING), "BB-000000000000", &value));
    cJSON *root = cJSON_Parse(T13A_PENDING);
    cJSON *doc = cJSON_GetObjectItem(root, "document");
    cJSON_ReplaceItemInObject(doc, "revision", cJSON_CreateBool(true));
    char *bad = cJSON_PrintUnformatted(root);
    TEST_ASSERT_NOT_EQUAL(ESP_OK, device_setup_parse(bad, strlen(bad), DEVICE, &value));
    cJSON_free(bad); cJSON_Delete(root);
    root = cJSON_Parse(T13A_PENDING); doc = cJSON_GetObjectItem(root, "document");
    cJSON_ReplaceItemInObject(doc, "revision", cJSON_CreateNumber(2));
    bad = cJSON_PrintUnformatted(root);
    TEST_ASSERT_NOT_EQUAL(ESP_OK, device_setup_parse(bad, strlen(bad), DEVICE, &value));
    cJSON_free(bad); cJSON_Delete(root);
}

static void test_t13a_persistent_pending_confirmation_and_versions(void)
{
    t13a_reset_nvs();
    device_setup_config_t pending, confirmed, loaded, next;
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_parse(T13A_PENDING, strlen(T13A_PENDING), DEVICE, &pending));
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_parse(T13A_CONFIRMED, strlen(T13A_CONFIRMED), DEVICE, &confirmed));
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_parse(T13A_NEXT, strlen(T13A_NEXT), DEVICE, &next));
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_save(&pending));
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_load(DEVICE, &loaded)); TEST_ASSERT_EQUAL(0, loaded.confirmed);
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_save(&confirmed));
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_load(DEVICE, &loaded)); TEST_ASSERT_EQUAL(1, loaded.confirmed);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, device_setup_save(&pending));
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_save(&next));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, device_setup_save(&confirmed));
    TEST_ASSERT_NOT_EQUAL(ESP_OK, device_setup_load("BB-000000000000", &loaded));
}

static void test_t13a_interrupted_configuration_store(void)
{
    device_setup_config_t confirmed, next, loaded;
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_parse(T13A_CONFIRMED, strlen(T13A_CONFIRMED), DEVICE, &confirmed));
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_parse(T13A_NEXT, strlen(T13A_NEXT), DEVICE, &next));
    for (int boundary = 1; boundary <= 2; ++boundary) {
        for (int after = 0; after <= 1; ++after) {
            t13a_reset_nvs(); TEST_ASSERT_EQUAL(ESP_OK, device_setup_save(&confirmed));
            t13a_fail_write(boundary, after);
            TEST_ASSERT_NOT_EQUAL(ESP_OK, device_setup_save(&next));
            t13a_fail_write(0, false);
            TEST_ASSERT_EQUAL(ESP_OK, device_setup_load(DEVICE, &loaded));
            TEST_ASSERT_TRUE((loaded.revision == 1 && loaded.confirmed == 1) ||
                             (loaded.revision == 2 && loaded.confirmed == 0));
        }
    }
}

static void test_t13a_real_pss_signature_verifies(void)
{
    const uint8_t message[] = "BB-SETUP-V1\nsynthetic signing interoperability";
    uint8_t signature[512], hash[32]; size_t size, hash_size;
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_sign(T13A_KEY, message, sizeof(message)-1, signature, sizeof(signature), &size));
    TEST_ASSERT_EQUAL(256, size);
    mbedtls_pk_context key; mbedtls_pk_init(&key);
    /* Verification must import an explicitly parsed public key. In Mbed TLS 4
     * parsing a private key does not populate the public raw-key buffer. */
    TEST_ASSERT_EQUAL(0, mbedtls_pk_parse_public_key(&key,
        (const uint8_t *)T13A_PUBLIC_KEY, sizeof(T13A_PUBLIC_KEY)));
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    TEST_ASSERT_EQUAL(0, mbedtls_pk_get_psa_attributes(&key, PSA_KEY_USAGE_VERIFY_HASH, &attributes));
    psa_set_key_algorithm(&attributes, PSA_ALG_RSA_PSS(PSA_ALG_SHA_256));
    mbedtls_svc_key_id_t id = 0;
    TEST_ASSERT_EQUAL(0, mbedtls_pk_import_into_psa(&key, &attributes, &id));
    TEST_ASSERT_EQUAL(PSA_SUCCESS, psa_hash_compute(PSA_ALG_SHA_256, message, sizeof(message)-1, hash, sizeof(hash), &hash_size));
    TEST_ASSERT_EQUAL(PSA_SUCCESS, psa_verify_hash(id, PSA_ALG_RSA_PSS(PSA_ALG_SHA_256), hash, hash_size, signature, size));
    signature[0] ^= 1;
    TEST_ASSERT_NOT_EQUAL(PSA_SUCCESS, psa_verify_hash(id, PSA_ALG_RSA_PSS(PSA_ALG_SHA_256), hash, hash_size, signature, size));
    psa_destroy_key(id); psa_reset_key_attributes(&attributes); mbedtls_pk_free(&key);
}

static void test_t13a_challenge_domain_identity_and_expiry(void)
{
    char proof[1024];
    TEST_ASSERT_EQUAL(ESP_OK, device_setup_proof(T13A_CHALLENGE, strlen(T13A_CHALLENGE), DEVICE, "sync", NULL,
        T13A_NOW, T13A_KEY, proof, sizeof(proof)));
    TEST_ASSERT_NOT_NULL(strstr(proof, "challenge_id"));
    TEST_ASSERT_NOT_EQUAL(ESP_OK, device_setup_proof(T13A_CHALLENGE, strlen(T13A_CHALLENGE), DEVICE, "sync", NULL,
        T13A_NOW+61, T13A_KEY, proof, sizeof(proof)));
    TEST_ASSERT_NOT_EQUAL(ESP_OK, device_setup_proof(T13A_CHALLENGE, strlen(T13A_CHALLENGE), "BB-000000000000", "sync", NULL,
        T13A_NOW, T13A_KEY, proof, sizeof(proof)));
    cJSON *root = cJSON_Parse(T13A_CHALLENGE);
    cJSON *payload = cJSON_GetObjectItem(root, "payload");
    cJSON_ReplaceItemInObject(payload, "purpose", cJSON_CreateString("confirm"));
    char *bad = cJSON_PrintUnformatted(root);
    TEST_ASSERT_NOT_EQUAL(ESP_OK, device_setup_proof(bad, strlen(bad), DEVICE, "sync", NULL,
        T13A_NOW, T13A_KEY, proof, sizeof(proof)));
    cJSON_free(bad); cJSON_Delete(root);
}

void run_t13a_tests(void)
{
    RUN_TEST(test_t13a_configuration_digest_and_strict_fields);
    RUN_TEST(test_t13a_persistent_pending_confirmation_and_versions);
    RUN_TEST(test_t13a_interrupted_configuration_store);
    RUN_TEST(test_t13a_real_pss_signature_verifies);
    RUN_TEST(test_t13a_challenge_domain_identity_and_expiry);
    run_t13a_queue_tests();
}
