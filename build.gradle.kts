plugins {
    base
    `maven-publish`
}

// The files the test suites of the implementations read, at their paths in this repository: unpacked, the archive
// is a sparse checkout of rialto-spec.
val specZip = tasks.register<Zip>("specZip") {
    description = "Packs the test contracts, the JSON Schema and the contract specification."
    group = "build"
    archiveBaseName = "rialto-spec"
    from(layout.projectDirectory) {
        include("examples/**")
        include("spec/contract-1.0.0.schema.json")
        include("spec/contract.md")
    }
}

tasks.named("assemble") { dependsOn(specZip) }

publishing {
    publications {
        create<MavenPublication>("spec") {
            artifactId = "rialto-spec"
            artifact(specZip)
            pom {
                name = "Rialto Specification"
                description = "The test contracts, JSON Schema and contract specification of Rialto"
                url = "https://github.com/buijs-dev/rialto-spec"
                licenses {
                    license {
                        name = "Apache-2.0"
                        url = "https://www.apache.org/licenses/LICENSE-2.0"
                    }
                }
            }
        }
    }

    repositories {
        maven {
            name = "Repsy"
            url = uri("https://repo.repsy.io/mvn/buijs-dev/maven")
            credentials {
                username = providers.environmentVariable("REPSY_USERNAME").orNull
                password = providers.environmentVariable("REPSY_PASSWORD").orNull
            }
        }
    }
}
