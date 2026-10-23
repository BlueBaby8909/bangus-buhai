#include "unity.h"
#include "command_manager.h"
#include "telemetry.h"
#include "relay_control.h"
#include "cJSON.h"
#include <stdio.h>
#include <string.h>

extern void t14_reset_nvs(void);
extern void t13a_fail_write(int boundary, bool after);
static const char *DEVICE = "BB-14C19FC68C60";
static const char *BINDING = "97fcde45-4112-41d4-a509-17e5bb1c0d91";
static const char *BOOT = "11111111-1111-4111-8111-111111111111";
static const char *BOOT2 = "22222222-2222-4222-8222-222222222222";
static char wire[1024], saved[COMMAND_RESULT_MAX], ack[512];
static unsigned requests;
static bool completion_ready, binding_allowed;
static esp_err_t queue_error;
static relay_command_request_t request;
static relay_command_completion_t completed;
static int64_t clock_us;

static bool current(const char *binding) { return binding_allowed && !strcmp(binding, BINDING); }
esp_err_t __wrap_relay_control_request_command(const relay_command_request_t *value)
{
    ++requests; request = *value; return queue_error;
}
bool __wrap_relay_control_take_completion(relay_command_completion_t *out)
{
    if (!completion_ready) { return false; }
    *out = completed; completion_ready = false; return true;
}
esp_err_t __wrap_relay_control_get_state(relay_control_state_t *out)
{
    *out = (relay_control_state_t){.known = true, .mode = RELAY_MODE_AUTO}; return ESP_OK;
}
static void reset(void)
{
    command_manager_close(); telemetry_close(); t14_reset_nvs();
    requests = 0; completion_ready = false; binding_allowed = true; queue_error = ESP_OK;
    telemetry_config_t config = {DEVICE, BOOT, BINDING, "t14-test"};
    TEST_ASSERT_EQUAL(ESP_OK, telemetry_init(&config));
    TEST_ASSERT_EQUAL(ESP_OK, command_manager_init(DEVICE, BOOT, current));
    TEST_ASSERT_TRUE(command_timestamp("2026-10-22T01:00:01Z", &clock_us));
}
static void make(unsigned index, bool automatic)
{
    snprintf(wire, sizeof(wire), "{\"schema_version\":1,\"device_id\":\"%s\",\"binding_id\":\"%s\","
        "\"command_id\":\"00000000-0000-4000-8000-%012u\",\"type\":\"%s\",%s"
        "\"issued_at\":\"2026-10-22T01:00:00.000000Z\",\"expires_at\":\"2026-10-22T01:01:00Z\"}",
        DEVICE, BINDING, index, automatic ? "relay.auto" : "relay.set", automatic ? "" : "\"desired_on\":true,");
}
static const command_result_wire_t *peek(void)
{
    const command_result_wire_t *out;
    TEST_ASSERT_EQUAL(ESP_OK, command_manager_peek(&out)); return out;
}
static void acknowledge(void)
{
    cJSON *root = cJSON_Parse(peek()->payload);
    snprintf(ack, sizeof(ack), "{\"schema_version\":1,\"device_id\":\"%s\",\"boot_id\":\"%s\","
        "\"seq\":%.0f,\"event_kind\":\"command_result\",\"result\":\"stored\"}", DEVICE,
        cJSON_GetObjectItem(root, "boot_id")->valuestring, cJSON_GetObjectItem(root, "seq")->valuedouble);
    cJSON_Delete(root);
    TEST_ASSERT_EQUAL(ESP_OK, command_manager_ack(ack, strlen(ack)));
}
static void complete(const char *outcome, const char *reason, bool on)
{
    completed = (relay_command_completion_t){.token = request.token, .state = {.known=true,.on=on,
        .mode=request.automatic ? RELAY_MODE_AUTO : RELAY_MODE_MANUAL}, .result=outcome, .reason=reason,
        .completed_us=clock_us+1000000, .completed_uptime_ms=2000};
    completion_ready = true; command_manager_poll(clock_us+1000000, 2000);
}
static void test_t14_canonical_time_and_malformed_commands(void)
{
    reset(); int64_t value;
    TEST_ASSERT_TRUE(command_timestamp("2024-02-29T23:59:59.123456Z", &value));
    const char *bad[] = {"2025-02-29T00:00:00Z","2026-10-22T01:00:00.1234567Z","2026-10-22T01:00:00+00:00",
        "2026-10-22T01:00:60Z","2026-10-22T1:00:00Z"};
    for (unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);++i) { TEST_ASSERT_FALSE(command_timestamp(bad[i], &value)); }
    make(1,false); char *boolean = strstr(wire,"true"); memcpy(boolean,"null",4);
    TEST_ASSERT_NOT_EQUAL(ESP_OK, command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
    TEST_ASSERT_NOT_EQUAL(ESP_OK, command_manager_receive("{\"schema_version\":1,\"schema_version\":1}",39,BINDING,clock_us,1000));
    TEST_ASSERT_EQUAL(0, requests);
}
static void test_t14_durable_accept_apply_ack_and_duplicate(void)
{
    reset(); make(1,false);
    TEST_ASSERT_EQUAL(ESP_OK, command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
    TEST_ASSERT_EQUAL(1, requests); TEST_ASSERT_NOT_NULL(strstr(peek()->payload,"accepted"));
    strcpy(saved,peek()->payload); printf("T14_WIRE_JSON:%s\n",saved);
    uint32_t next; TEST_ASSERT_EQUAL(ESP_OK,telemetry_allocate_sequence(&next)); TEST_ASSERT_EQUAL(1,next);
    complete("applied","applied",true); TEST_ASSERT_EQUAL_STRING(saved,peek()->payload);
    acknowledge(); TEST_ASSERT_NOT_NULL(strstr(peek()->payload,"applied")); printf("T14_WIRE_JSON:%s\n",peek()->payload);
    acknowledge(); const command_result_wire_t *empty;
    TEST_ASSERT_EQUAL(ESP_ERR_NOT_FOUND,command_manager_peek(&empty));
    TEST_ASSERT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
    TEST_ASSERT_EQUAL(1,requests); TEST_ASSERT_EQUAL_STRING(saved,peek()->payload);
    char *desired=strstr(wire,"true"); memcpy(desired,"null",4);
    TEST_ASSERT_NOT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000)); TEST_ASSERT_EQUAL(1,requests);
}
static void test_t14_expired_unsynchronized_and_wrong_binding_never_queue(void)
{
    reset(); make(1,false);
    TEST_ASSERT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,clock_us+60000000,1000));
    TEST_ASSERT_NOT_NULL(strstr(peek()->payload,"command_expired")); acknowledge();
    make(2,false); TEST_ASSERT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,0,1000));
    TEST_ASSERT_NOT_NULL(strstr(peek()->payload,"clock_unsynchronized")); acknowledge();
    make(3,false); binding_allowed=false;
    TEST_ASSERT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
    TEST_ASSERT_NOT_NULL(strstr(peek()->payload,"binding_changed")); TEST_ASSERT_EQUAL(0,requests);
}
static void test_t14_auto_and_control_failure_results(void)
{
    reset(); make(1,true);
    TEST_ASSERT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
    TEST_ASSERT_TRUE(request.automatic); complete("applied","applied",false); acknowledge();
    TEST_ASSERT_NOT_NULL(strstr(peek()->payload,"\"observed_on\":false")); acknowledge();
    make(2,false); queue_error=ESP_ERR_TIMEOUT;
    TEST_ASSERT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
    acknowledge(); TEST_ASSERT_NOT_NULL(strstr(peek()->payload,"control_queue_unavailable"));
}
static void test_t14_reboot_fails_pending_without_reapplication(void)
{
    reset(); make(1,false);
    TEST_ASSERT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
    strcpy(saved,peek()->payload);
    telemetry_config_t config={DEVICE,BOOT2,BINDING,"t14-test"};
    TEST_ASSERT_EQUAL(ESP_OK,telemetry_init(&config));
    TEST_ASSERT_EQUAL(ESP_OK,command_manager_init(DEVICE,BOOT2,current));
    command_manager_poll(0,50); TEST_ASSERT_EQUAL(1,requests); TEST_ASSERT_EQUAL_STRING(saved,peek()->payload);
    acknowledge(); TEST_ASSERT_NOT_NULL(strstr(peek()->payload,"interrupted_by_restart"));
    TEST_ASSERT_NOT_NULL(strstr(peek()->payload,BOOT2));
}
static void test_t14_interrupted_admission_never_actuates(void)
{
    for(int boundary=1;boundary<=2;++boundary) { for(int after=0;after<=1;++after) {
        reset(); make(1,false); t13a_fail_write(boundary,after);
        TEST_ASSERT_NOT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
        TEST_ASSERT_EQUAL(0,requests); t13a_fail_write(0,false);
        TEST_ASSERT_EQUAL(ESP_OK,command_manager_init(DEVICE,BOOT2,current));
        command_manager_poll(0,50); TEST_ASSERT_EQUAL(0,requests);
    }}
}
static void test_t14_full_ledger_refuses_untracked_work(void)
{
    reset();
    for(unsigned i=0;i<COMMAND_CAPACITY;++i) {
        make(i,false); TEST_ASSERT_EQUAL(ESP_OK,command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
        complete("applied","applied",true);
    }
    make(99,false); TEST_ASSERT_EQUAL(ESP_ERR_NO_MEM,command_manager_receive(wire,strlen(wire),BINDING,clock_us,1000));
    TEST_ASSERT_EQUAL(COMMAND_CAPACITY,requests);
}
static void test_t14_execution_rechecks_binding_and_two_clocks(void)
{
    reset(); relay_command_request_t value={.issued_us=10,.expires_us=100,.deadline_ms=90,.binding_current=current};
    strcpy(value.binding_id,BINDING);
    TEST_ASSERT_NULL(relay_command_rejection(&value,50,50));
    TEST_ASSERT_EQUAL_STRING("command_expired",relay_command_rejection(&value,100,50));
    TEST_ASSERT_EQUAL_STRING("command_expired",relay_command_rejection(&value,50,90));
    TEST_ASSERT_EQUAL_STRING("command_expired",relay_command_rejection(&value,9,50));
    binding_allowed=false;
    TEST_ASSERT_EQUAL_STRING("binding_changed",relay_command_rejection(&value,50,50));
}
void run_t14_tests(void)
{
    RUN_TEST(test_t14_canonical_time_and_malformed_commands);
    RUN_TEST(test_t14_durable_accept_apply_ack_and_duplicate);
    RUN_TEST(test_t14_expired_unsynchronized_and_wrong_binding_never_queue);
    RUN_TEST(test_t14_auto_and_control_failure_results);
    RUN_TEST(test_t14_reboot_fails_pending_without_reapplication);
    RUN_TEST(test_t14_interrupted_admission_never_actuates);
    RUN_TEST(test_t14_full_ledger_refuses_untracked_work);
    RUN_TEST(test_t14_execution_rechecks_binding_and_two_clocks);
}
