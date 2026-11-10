/* Count CPython object allocations (PYMEM_DOMAIN_OBJ).
 *
 * The hook chains to the allocator it replaces, so pymalloc and freelists keep
 * their normal behavior. malloc, calloc, and realloc are counted. free is not.
 * The hook itself does not allocate.
 */
#define _GNU_SOURCE

#include <dlfcn.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
    void *ctx;
    void *(*malloc)(void *ctx, size_t size);
    void *(*calloc)(void *ctx, size_t nelem, size_t elsize);
    void *(*realloc)(void *ctx, void *ptr, size_t new_size);
    void (*free)(void *ctx, void *ptr);
} PyMemAllocatorEx;

typedef void (*get_allocator_fn)(int domain, PyMemAllocatorEx *allocator);
typedef void (*set_allocator_fn)(int domain, PyMemAllocatorEx *allocator);

/* Include/cpython/pymem.h: RAW=0, MEM=1, OBJ=2. */
enum { PYMEM_DOMAIN_OBJ = 2 };

static PyMemAllocatorEx old_allocator;
static int installed = 0;
static int enabled = 0;
static uint64_t alloc_count = 0;

static void *hook_malloc(void *ctx, size_t size) {
    (void)ctx;
    if (enabled) {
        alloc_count++;
    }
    return old_allocator.malloc(old_allocator.ctx, size);
}

static void *hook_calloc(void *ctx, size_t nelem, size_t elsize) {
    (void)ctx;
    if (enabled) {
        alloc_count++;
    }
    return old_allocator.calloc(old_allocator.ctx, nelem, elsize);
}

static void *hook_realloc(void *ctx, void *ptr, size_t new_size) {
    (void)ctx;
    /* A positive new size is an allocation. Size 0 is a free. */
    if (enabled && new_size) {
        alloc_count++;
    }
    return old_allocator.realloc(old_allocator.ctx, ptr, new_size);
}

static void hook_free(void *ctx, void *ptr) {
    (void)ctx;
    old_allocator.free(old_allocator.ctx, ptr);
}

void alloc_install(void) {
    get_allocator_fn get_allocator;
    set_allocator_fn set_allocator;
    PyMemAllocatorEx hook;

    if (installed) {
        return;
    }
    get_allocator = (get_allocator_fn)dlsym(RTLD_DEFAULT, "PyMem_GetAllocator");
    set_allocator = (set_allocator_fn)dlsym(RTLD_DEFAULT, "PyMem_SetAllocator");
    if (get_allocator == NULL || set_allocator == NULL) {
        return;
    }
    get_allocator(PYMEM_DOMAIN_OBJ, &old_allocator);
    hook.ctx = NULL;
    hook.malloc = hook_malloc;
    hook.calloc = hook_calloc;
    hook.realloc = hook_realloc;
    hook.free = hook_free;
    set_allocator(PYMEM_DOMAIN_OBJ, &hook);
    installed = 1;
}

int alloc_installed(void) {
    return installed;
}

void alloc_reset(void) {
    alloc_count = 0;
    enabled = 1;
}

uint64_t alloc_stop(void) {
    enabled = 0;
    return alloc_count;
}
