#include <iostream>
#include <lustre/lustreapi.h>
#include <string>

using namespace std;

extern "C" {
    int get_file_ost(const char* file_path) {
        cout << "Getting OST for file: " << file_path << endl;
        struct llapi_layout *layout = llapi_layout_get_by_path(file_path, 0);
        uint64_t ost_index;

        if (layout == NULL) {
            cerr << "Error getting layout for file: " << file_path << endl;
            return -1;
        }

        llapi_layout_comp_use(layout, 1);
        llapi_layout_ost_index_get(layout, 0, &ost_index);
        cout << "OST index: " << ost_index << endl;
        return ost_index;
    }
}
