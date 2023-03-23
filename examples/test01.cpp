#include <iostream>

const int CLANG_INDEX = 0;

class Node {
    private:
        int x, y;
    public:
        void setX(int);
        void setY(int);
        void setXY(int x, int y);
        int getX();
        int getY();
};

void Node::setX(int x) {
    this->x = x;
}

void Node::setY(int y) {
    this->y = y;
}

void Node::setXY(int x, int y) {
    this->setX(x);
    this->setY(y);
}

int Node::getX() { 
    return this->x;
 }

 int Node::getY() {
    return this->y;
 }

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
