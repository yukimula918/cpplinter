#include <iostream>

const int CLANG_INDEX = 0;

// main implements the entry of this simple test program.
int main() {
    std::cout << "Hello, world!" << '\n';
    return CLANG_INDEX;
}

int add(int x, int y, float z) {
    if (x > 0) {
        return (int) z;
    } else if (y <= 0 && z >= 100.0) {
        return x * 2 * y;
    }
    return 0;
}

int strlength(const char seq[]) {
    int i = 0;
    while (seq[i] != '\0') {
        i++;
    }
    return i;
}
