#include "module_manager.hpp"

#define __DEBUG
#include "common/debug.hpp"

module_manager_t::module_manager_t() { }

void module_manager_t::add_default_modules(const config_t &cfg) {
    watchdog = new client_watchdog_t(cfg);
    add_module([this](const command_t &c) { return watchdog->process_command(c); });
    transfer = new transfer_module_t(cfg);
    add_module([this](const command_t &c) { return transfer->process_command(c); });
}

module_manager_t::~module_manager_t() {
    delete watchdog;
    delete transfer;
}

int module_manager_t::notify_command(const command_t &c) {
    return *sig(c);
}
