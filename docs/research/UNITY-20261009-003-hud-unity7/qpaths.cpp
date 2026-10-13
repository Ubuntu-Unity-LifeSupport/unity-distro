// qpaths NAME - print what hud-service's desktop-file lookup returns with the current environment:
// QStandardPaths::locate(QStandardPaths::ApplicationsLocation, NAME) (ApplicationImpl::desktopPath, +unity6),
// and the directories Qt searches (standardLocations).
#include <QCoreApplication>
#include <QStandardPaths>
#include <QTextStream>

int main(int argc, char **argv) {
	QCoreApplication app(argc, argv);
	QTextStream out(stdout);
	const QString name = argc > 1 ? QString::fromLocal8Bit(argv[1]) : QStringLiteral("x.desktop");
	out << "XDG_DATA_HOME=" << qgetenv("XDG_DATA_HOME") << " XDG_DATA_DIRS=" << qgetenv("XDG_DATA_DIRS") << "\n";
	out << "  standardLocations(ApplicationsLocation): "
	    << QStandardPaths::standardLocations(QStandardPaths::ApplicationsLocation).join(" ") << "\n";
	out << "  locate(" << name << "): \"" << QStandardPaths::locate(QStandardPaths::ApplicationsLocation, name)
	    << "\"\n";
	return 0;
}
